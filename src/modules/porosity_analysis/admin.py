from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.contrib import messages
from src.modules.porosity_analysis.models import PorosityAnalysis
from src.modules.porosity_analysis.tasks import run_porosity_analysis


@admin.register(PorosityAnalysis)
class PorosityAnalysisAdmin(admin.ModelAdmin):
    """Административный интерфейс для анализа пористости"""
    
    list_display = [
        'id', 'name', 'status', 'porosity_percentage', 'number_of_pores',
        'created_at', 'file_size_display'
    ]
    list_filter = ['status', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = [
        'id', 'created_at', 'original_image_uuid', 'results_uuid',
        'porosity_percentage', 'number_of_pores', 'average_pore_size',
        'max_pore_size', 'min_pore_size', 'pore_density',
        'average_interpore_distance', 'error_message'
    ]
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'description', 'created_at')
        }),
        ('Файлы', {
            'fields': ('original_image_uuid', 'results_uuid')
        }),
        ('Параметры анализа', {
            'fields': ('scale_value', 'pixels_per_micron')
        }),
        ('Результаты', {
            'fields': (
                'porosity_percentage', 'number_of_pores', 'average_pore_size',
                'max_pore_size', 'min_pore_size', 'pore_density',
                'average_interpore_distance'
            )
        }),
        ('Статус', {
            'fields': ('status', 'error_message')
        }),
    )
    
    actions = ['restart_analysis', 'mark_as_pending', 'mark_as_failed']
    
    def file_size_display(self, obj):
        """Отображение размера файла"""
        if obj.original_image_path and obj.original_image_path.exists():
            size_mb = obj.original_image_path.size / (1024 * 1024)
            return f"{size_mb:.2f} МБ"
        return "Файл не найден"
    file_size_display.short_description = "Размер файла"
    
    def restart_analysis(self, request, queryset):
        """Перезапуск выбранных анализов"""
        count = 0
        for analysis in queryset:
            if analysis.status in ['failed', 'pending']:
                analysis.status = 'pending'
                analysis.error_message = ''
                analysis.save()
                run_porosity_analysis.delay(analysis.id)
                count += 1
        
        messages.success(request, f"Перезапущено {count} анализов")
    restart_analysis.short_description = "Перезапустить выбранные анализы"
    
    def mark_as_pending(self, request, queryset):
        """Пометить как ожидающие"""
        count = queryset.update(status='pending', error_message='')
        messages.success(request, f"Помечено как ожидающие: {count} анализов")
    mark_as_pending.short_description = "Пометить как ожидающие"
    
    def mark_as_failed(self, request, queryset):
        """Пометить как неудачные"""
        count = queryset.update(status='failed', error_message='Отменено администратором')
        messages.success(request, f"Помечено как неудачные: {count} анализов")
    mark_as_failed.short_description = "Пометить как неудачные"
    
    def get_queryset(self, request):
        """Оптимизация запросов"""
        return super().get_queryset(request).select_related()
    
    def has_add_permission(self, request):
        """Запрет создания через админку"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Разрешение удаления"""
        return True
    
    def response_change(self, request, obj):
        """Обработка изменений"""
        if "_restart" in request.POST:
            obj.status = 'pending'
            obj.error_message = ''
            obj.save()
            run_porosity_analysis.delay(obj.id)
            messages.success(request, "Анализ перезапущен")
            return HttpResponseRedirect(".")
        return super().response_change(request, obj)
    
    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        """Добавление кнопки перезапуска"""
        extra_context = extra_context or {}
        extra_context['show_restart_button'] = True
        return super().changeform_view(request, object_id, form_url, extra_context) 