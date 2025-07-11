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
        
        # Получаем объект анализа
        analysis = PorosityAnalysis.objects.get(id=analysis_id)
        
        # Обновляем статус на "обрабатывается"
        analysis.status = 'processing'
        analysis.save()
        
        logger.info(f"Начинаем анализ пористости для ID: {analysis_id}")
        
        # Проверяем существование исходного изображения
        if not os.path.exists(analysis.original_image_path):
            raise FileNotFoundError(f"Исходное изображение не найдено: {analysis.original_image_path}")
        
        # Импортируем необходимые модули для анализа
        from .scripts.main import run_analysis
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
        
        # Запускаем анализ
        logger.warning(f"Путь к изображению: {analysis.original_image_path}, существует: {os.path.exists(analysis.original_image_path)}")
        results = run_analysis(config)

        # Логируем результаты для отладки
        logger.warning(f"Результаты анализа: {results}")

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
        logger.warning(f"Сохраняемые значения:")
        logger.warning(f"  - porosity_percentage: {porosity_percentage}")
        logger.warning(f"  - number_of_pores: {number_of_pores}")
        logger.warning(f"  - average_pore_size: {average_pore_size}")
        logger.warning(f"  - max_pore_size: {max_pore_size}")
        logger.warning(f"  - min_pore_size: {min_pore_size}")
        logger.warning(f"  - pore_density: {pore_density}")
        logger.warning(f"  - average_interpore_distance: {average_interpore_distance}")
        
        analysis.porosity_percentage = porosity_percentage
        analysis.number_of_pores = number_of_pores
        analysis.average_pore_size = average_pore_size
        analysis.max_pore_size = max_pore_size
        analysis.min_pore_size = min_pore_size
        analysis.pore_density = pore_density
        analysis.average_interpore_distance = average_interpore_distance
        analysis.status = 'completed'
        analysis.save()
        
        # Генерируем отчеты
        try:
            from .report_generator import PorosityReportGenerator
            report_generator = PorosityReportGenerator(analysis)
            reports = report_generator.generate_reports()
            logger.info(f"Отчеты сгенерированы: {reports}")
        except Exception as e:
            logger.error(f"Ошибка при генерации отчетов для анализа {analysis_id}: {e}")
            # Не прерываем процесс, если отчеты не удалось создать
        
        logger.info(f"Анализ пористости завершен успешно для ID: {analysis_id}")
        
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