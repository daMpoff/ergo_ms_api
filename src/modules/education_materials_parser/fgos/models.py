import uuid
from django.db import models
from django.utils import timezone


class FgosDocument(models.Model):
    """Модель для хранения документов ФГОС"""
    
    # Уникальный идентификатор файла
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, verbose_name="UUID файла")
    
    # Основная информация
    title = models.CharField(max_length=500, verbose_name="Название ФГОС")
    code = models.CharField(max_length=50, null=True, blank=True, verbose_name="Код специальности")
    level = models.CharField(max_length=100, null=True, blank=True, verbose_name="Уровень образования")
    field_of_study = models.CharField(max_length=200, null=True, blank=True, verbose_name="Область изучения")
    
    # Информация о файле
    filename = models.CharField(max_length=255, verbose_name="Имя файла")
    file_size = models.BigIntegerField(null=True, blank=True, verbose_name="Размер файла в байтах")
    
    # Ссылки
    source_url = models.URLField(verbose_name="Исходная ссылка на страницу")
    download_url = models.URLField(verbose_name="Ссылка для скачивания PDF")
    
    # Даты и статус
    published_date = models.DateField(null=True, blank=True, verbose_name="Дата публикации")
    parsed_at = models.DateTimeField(default=timezone.now, verbose_name="Время парсинга")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Время обновления")
    
    # Статус файла
    is_downloaded = models.BooleanField(default=False, verbose_name="Файл скачан")
    download_error = models.TextField(null=True, blank=True, verbose_name="Ошибка скачивания")
    
    # Дополнительные метаданные
    order_number = models.CharField(max_length=100, null=True, blank=True, verbose_name="Номер приказа")
    ministry = models.CharField(max_length=200, null=True, blank=True, verbose_name="Министерство")
    registration_number = models.CharField(max_length=100, null=True, blank=True, verbose_name="Регистрационный номер")
    
    class Meta:
        verbose_name = "Документ ФГОС"
        verbose_name_plural = "Документы ФГОС"
        ordering = ['-parsed_at']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['level']),
            models.Index(fields=['parsed_at']),
            models.Index(fields=['is_downloaded']),
        ]
    
    def __str__(self):
        return f"{self.code} - {self.title}"
    
    def get_file_path(self):
        """Возвращает путь к файлу в файловой системе"""
        return f"education_materials_parser/{self.uuid}.pdf"
    
    @property
    def file_path(self):
        """Свойство для получения пути к файлу"""
        return self.get_file_path()


class FgosParsingSession(models.Model):
    """Модель для отслеживания сессий парсинга"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    started_at = models.DateTimeField(default=timezone.now, verbose_name="Время начала")
    finished_at = models.DateTimeField(null=True, blank=True, verbose_name="Время окончания")
    
    # Статистика парсинга
    total_pages_found = models.IntegerField(default=0, verbose_name="Всего найдено страниц")
    total_documents_found = models.IntegerField(default=0, verbose_name="Всего найдено документов")
    new_documents_added = models.IntegerField(default=0, verbose_name="Добавлено новых документов")
    documents_updated = models.IntegerField(default=0, verbose_name="Обновлено документов")
    files_downloaded = models.IntegerField(default=0, verbose_name="Скачано файлов")
    download_errors = models.IntegerField(default=0, verbose_name="Ошибок скачивания")
    
    # Статус сессии
    status = models.CharField(
        max_length=20,
        choices=[
            ('running', 'Выполняется'),
            ('completed', 'Завершено'),
            ('failed', 'Ошибка'),
            ('cancelled', 'Отменено'),
        ],
        default='running',
        verbose_name="Статус"
    )
    
    error_message = models.TextField(null=True, blank=True, verbose_name="Сообщение об ошибке")
    
    class Meta:
        verbose_name = "Сессия парсинга ФГОС"
        verbose_name_plural = "Сессии парсинга ФГОС"
        ordering = ['-started_at']
    
    def __str__(self):
        return f"Сессия {self.id} - {self.status} ({self.started_at})"
    
    def mark_completed(self):
        """Отметить сессию как завершенную"""
        self.status = 'completed'
        self.finished_at = timezone.now()
        self.save()
    
    def mark_failed(self, error_message=None):
        """Отметить сессию как провалившуюся"""
        self.status = 'failed'
        self.finished_at = timezone.now()
        if error_message:
            self.error_message = error_message
        self.save() 