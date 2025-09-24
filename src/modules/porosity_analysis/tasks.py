import os
import logging

# Настройка Matplotlib для работы в фоновом режиме (без GUI)
# ДОЛЖНО БЫТЬ ДО ИМПОРТА matplotlib
import matplotlib
matplotlib.use('Agg')  # Используем non-interactive backend

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from src.modules.porosity_analysis.models import PorosityAnalysis
from src.modules.porosity_analysis.config import PorosityAnalysisConfig
from src.modules.porosity_analysis.utils import is_cancelled, clear_cancel_flag

# Настраиваем логгер для задач анализа пористости
logger = logging.getLogger('celery.task.porosity_analysis')


def check_concurrent_analyses_limit():
    """
    Проверяет, не превышено ли максимальное количество одновременных анализов
    """
    # Убрана проверка лимитов - всегда возвращаем True
    return True


@shared_task(bind=True, max_retries=3)
def run_porosity_analysis(self, analysis_id):
    """
    Асинхронная задача для выполнения анализа пористости
    
    Args:
        analysis_id (int): ID анализа в базе данных
    """
    try:
        # Убрана проверка лимита одновременных анализов
        
        # Отмена до старта
        if is_cancelled(analysis_id):
            logger.info(f"Анализ {analysis_id} отменен до запуска. Завершаем задачу.")
            return

        # Получаем объект анализа
        analysis = PorosityAnalysis.objects.get(id=analysis_id)
        
        # Обновляем статус на "обрабатывается" и фиксируем время старта
        analysis.status = 'processing'
        analysis.start_time = timezone.now()
        analysis.save()
        
        logger.info(f"Начинаем анализ пористости для ID: {analysis_id}")
        
        # Проверяем существование исходного изображения
        if not os.path.exists(analysis.original_image_path):
            raise FileNotFoundError(f"Исходное изображение не найдено: {analysis.original_image_path}")
        
        # Импортируем необходимые модули для анализа
        from .scripts.porosity_analyzer import integrated_analysis
        from .scripts.config import AnalysisConfig
        
        # Создаем конфигурацию анализа
        config = AnalysisConfig(
            input_image_path=analysis.original_image_path,
            output_directory=analysis.results_directory,
            scale_value=analysis.scale_value,
            pixels_per_micron=analysis.pixels_per_micron
        )
        
        # Создаем директорию для результатов если её нет
        os.makedirs(analysis.results_directory, exist_ok=True)
        
        # Пробрасываем идентификатор анализа в окружение для внутренних проверок отмены
        os.environ['POROSITY_ANALYSIS_ID'] = str(analysis_id)

        # Запускаем анализ
        logger.warning(f"Путь к изображению: {analysis.original_image_path}, существует: {os.path.exists(analysis.original_image_path)}")
        # Внутренняя обертка, позволяющая периодически проверять отмену
        results = integrated_analysis(
            image_path=config.input_image_path,
            scale_value=config.scale_value,
            save_directory=config.output_directory
        )

        # Логируем результаты для отладки
        # Не логируем весь объект результатов (может быть очень большим)
        try:
            result_keys = list(results.keys()) if isinstance(results, dict) else None
            logger.info(f"Результаты анализа получены. Ключи: {result_keys}")
        except Exception:
            logger.info("Результаты анализа получены.")

        # Если во время выполнения пришла отмена — завершаем без ошибки
        if is_cancelled(analysis_id):
            logger.info(f"Анализ {analysis_id} был отменен во время выполнения. Корректное завершение без сохранения результатов.")
            clear_cancel_flag(analysis_id)
            return

        if not results:
            logger.error(f"Анализ не выполнен или произошла ошибка для анализа {analysis_id} (см. выше в логах)")
            analysis.status = 'failed'
            analysis.error_message = f"Анализ не выполнен или произошла ошибка (см. выше в логах)"
            analysis.save()
            return  # Не продолжаем обновлять поля результата

        # Обновляем результаты в базе данных
        porosity_percentage = results.get('porosity_percentage')
        number_of_pores = results.get('number_of_pores')
        average_pore_size = results.get('mean_pore_size_microns')
        max_pore_size = results.get('max_pore_size_microns')
        min_pore_size = results.get('min_pore_size_microns')
        pore_density = results.get('pore_density')
        average_interpore_distance = results.get('average_interpore_distance')
        
        # Логируем значения для отладки
        logger.debug("Сохраняемые значения: porosity=%s, pores=%s, avg_size=%s, max=%s, min=%s, density=%s, interpore=%s",
                     porosity_percentage, number_of_pores, average_pore_size, max_pore_size, min_pore_size, pore_density, average_interpore_distance)
        
        analysis.porosity_percentage = porosity_percentage
        analysis.number_of_pores = number_of_pores
        analysis.average_pore_size = average_pore_size
        analysis.max_pore_size = max_pore_size
        analysis.min_pore_size = min_pore_size
        analysis.pore_density = pore_density
        analysis.average_interpore_distance = average_interpore_distance
        analysis.status = 'completed'
        analysis.end_time = timezone.now()
        try:
            if analysis.start_time and analysis.end_time:
                analysis.duration_seconds = int((analysis.end_time - analysis.start_time).total_seconds())
        except Exception:
            pass
        analysis.save()
        
        # Генерируем отчеты (встраиваем изображения напрямую, без сохранения PNG)
        try:
            from .report_generator import PorosityReportGenerator
            report_generator = PorosityReportGenerator(analysis, results)
            reports = report_generator.generate_reports()
            logger.info(f"Отчеты сгенерированы: {reports}")
        except Exception as e:
            logger.error(f"Ошибка при генерации отчетов для анализа {analysis_id}: {e}")
            # Пытаемся создать только DOCX отчет если полная генерация не удалась
            try:
                logger.info(f"Пытаемся создать только DOCX отчет для анализа {analysis_id}")
                from .report_generator import PorosityReportGenerator
                report_generator = PorosityReportGenerator(analysis, results)
                docx_report = report_generator.generate_single_report('docx')
                if docx_report:
                    logger.info(f"DOCX отчет создан: {docx_report}")
                else:
                    logger.warning(f"Не удалось создать DOCX отчет для анализа {analysis_id}")
            except Exception as docx_error:
                logger.error(f"Критическая ошибка при создании отчетов для анализа {analysis_id}: {docx_error}")
            # Не прерываем процесс, если отчеты не удалось создать

        logger.info(f"Анализ пористости завершен успешно для ID: {analysis_id}")
        clear_cancel_flag(analysis_id)
        
    except PorosityAnalysis.DoesNotExist:
        logger.error(f"Анализ с ID {analysis_id} не найден")
        raise
    except FileNotFoundError as e:
        logger.error(f"Ошибка файла для анализа {analysis_id}: {str(e)}")
        analysis.status = 'failed'
        analysis.error_message = f"Файл не найден: {str(e)}"
        analysis.save()
        raise
    except Exception as e:
        logger.error(f"Ошибка при выполнении анализа {analysis_id}: {str(e)}")
        
        # Обновляем статус на "ошибка"
        analysis.status = 'failed'
        analysis.error_message = str(e)
        analysis.save()
        
        # Повторяем задачу если не превышено максимальное количество попыток
        retry_delay = PorosityAnalysisConfig.get_retry_delay()
        if self.request.retries < self.max_retries:
            logger.info(f"Повторная попытка анализа {analysis_id}, попытка {self.request.retries + 1}")
            raise self.retry(countdown=retry_delay * (2 ** self.request.retries))  # Экспоненциальная задержка
        else:
            logger.error(f"Анализ {analysis_id} завершился неудачно после {self.max_retries} попыток")
            raise


@shared_task
def cleanup_failed_analyses():
    """
    Периодическая задача для очистки неудачных анализов старше указанного количества дней
    """
    from datetime import timedelta
    
    cleanup_days = PorosityAnalysisConfig.get_cleanup_days()
    cutoff_date = timezone.now() - timedelta(days=cleanup_days)
    failed_analyses = PorosityAnalysis.objects.filter(
        status='failed',
        created_at__lt=cutoff_date
    )
    
    count = failed_analyses.count()
    if count > 0:
        failed_analyses.delete()
        logger.info(f"Удалено {count} неудачных анализов старше 7 дней")
    else:
        logger.info("Нет неудачных анализов для удаления")


@shared_task
def validate_analysis_files():
    """
    Периодическая задача для проверки целостности файлов анализов
    """
    analyses = PorosityAnalysis.objects.filter(status='completed')
    
    for analysis in analyses:
        if not os.path.exists(analysis.original_image_path):
            logger.warning(f"Исходное изображение для анализа {analysis.id} не найдено")
            analysis.status = 'failed'
            analysis.error_message = "Исходное изображение удалено"
            analysis.save()
        
        if not os.path.exists(analysis.results_directory):
            logger.warning(f"Директория результатов для анализа {analysis.id} не найдена")
            analysis.status = 'failed'
            analysis.error_message = "Директория результатов удалена"
            analysis.save() 