import os
import time
from pathlib import Path

from django.core.management.base import BaseCommand

from src.config.settings.static import MEDIA_ROOT
from src.modules.video_analysis.tasks import translate_video_analysis

VIDEO_ANALYSIS_ROOT = Path(MEDIA_ROOT) / 'video_analysis'
INITIAL_VIDEO_DIR = VIDEO_ANALYSIS_ROOT / 'initial_video'
RESULTS_DIR = VIDEO_ANALYSIS_ROOT / 'results'

class Command(BaseCommand):
    help = 'Переводит видео из media/video_analysis/initial_video с русских субтитров на французские и добавляет их к видео через Celery.'

    def add_arguments(self, parser):
        parser.add_argument('video_name', type=str, help='Имя видеофайла (например, input.mp4)')
        parser.add_argument('--output-dir', type=str, help='Директория для сохранения результатов (опционально)')
        parser.add_argument('--wait', action='store_true', help='Ждать завершения обработки')
        parser.add_argument('--gpu', action='store_true', help='Использовать GPU для моделей перевода')
        parser.add_argument('--cpu', action='store_true', help='Принудительно использовать CPU')

    def handle(self, *args, **options):
        start_time = time.time()
        
        video_name = options['video_name']
        output_dir = options.get('output_dir')
        wait_for_completion = options.get('wait')
        
        # Определяем использование GPU
        use_gpu = None
        if options.get('gpu'):
            use_gpu = True
        elif options.get('cpu'):
            use_gpu = False
        # Если не указано ни --gpu, ни --cpu, используем настройки по умолчанию из конфига
        
        video_path = INITIAL_VIDEO_DIR / video_name

        if not os.path.exists(video_path):
            self.stderr.write(self.style.ERROR(f'Файл {video_path} не найден!'))
            self.stdout.write(f'Убедитесь, что файл находится в папке: {INITIAL_VIDEO_DIR}')
            return

        self.stdout.write(f'Запуск обработки видео: {video_name}')
        self.stdout.write(f'Путь к видео: {video_path}')
        
        # Показываем информацию о GPU/CPU
        if use_gpu is True:
            self.stdout.write('Использование: GPU (принудительно)')
        elif use_gpu is False:
            self.stdout.write('Использование: CPU (принудительно)')
        else:
            self.stdout.write('Использование: настройки по умолчанию из конфига')
        
        if output_dir:
            self.stdout.write(f'Директория для результатов: {output_dir}')
        else:
            self.stdout.write(f'Результаты будут сохранены в: {RESULTS_DIR}')
        
        # Запускаем задачу в Celery
        task = translate_video_analysis.delay(video_name, 1, use_gpu)
        
        self.stdout.write(f'Задача запущена с ID: {task.id}')
        self.stdout.write(f'Статус: {task.status}')
        
        if wait_for_completion:
            self.stdout.write('Ожидание завершения обработки...')
            
            # Ждем завершения с обновлением статуса
            while not task.ready():
                try:
                    result = task.result
                    if hasattr(result, 'get'):
                        state = result.get('state', 'PENDING')
                        progress = result.get('progress', 0)
                        self.stdout.write(f'Прогресс: {progress}% - {state}')
                except Exception:
                    pass
                time.sleep(2)
            result = task.get()
            if result['status'] == 'completed':
                self.stdout.write(self.style.SUCCESS('Обработка завершена успешно!'))
                self.stdout.write(f'UUID анализа: {result["analysis_uuid"]}')
                self.stdout.write(f'Папка с результатами: {result["results_dir"]}')
                self.stdout.write(f'Файл субтитров: {result["srt_file"]}')
                self.stdout.write(f'Выходное видео: {result["output_video"]}')
                self.stdout.write(f'Количество субтитров: {result["subtitle_count"]}')
                total_time = time.time() - start_time
                self.stdout.write(f'Общее время выполнения: {total_time:.2f} сек ({total_time/60:.1f} мин)')
            else:
                self.stderr.write(self.style.ERROR(f'Ошибка при обработке: {result["message"]}'))
        else:
            self.stdout.write(self.style.SUCCESS('Задача поставлена в очередь на обработку.'))
            self.stdout.write(f'Для проверки статуса используйте ID задачи: {task.id}')
            self.stdout.write('Или запустите команду с флагом --wait для ожидания завершения.') 