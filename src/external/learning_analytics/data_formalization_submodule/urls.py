from django.urls import path
from src.external.learning_analytics.data_formalization_submodule.views import (
    SpecialityView,
    CurriculumView,
    TechnologyView,
    CompetencyView,
    BaseDisciplineView,
    DisciplineView,
    VacancyView,
    ACMView,
    VCMView,
    UCMView,
    LoadSampleTechnologyData,
    LoadSampleSpecialityData,
    LoadSampleCurriculumData,
    LoadSampleCompetencyData,
    LoadSampleBaseDisciplineData,
    LoadSampleDisciplineData,
    LoadSampleVacancyData,
    LoadSampleACMData,
    LoadSampleVCMData,
    LoadSampleUCMData,
    DisciplineTechnologyRelationView,
    DisciplineCompetencyRelationView,
    VacancyTechnologyRelationView,
    VacancyCompetencyRelationView,
    VCMTechnologyRelationView,
    VCMCompetencyRelationView,

    ImportHistoryView,
    ImportHistoryGetView,
    ImportStatsView,
    ImportStatsGetView,

    ExcelUploadView,
    ProcessExcelDataView,
)

urlpatterns = [
    path('specialities/', SpecialityView.as_view({'get': 'list', 'post': 'create'}), name='specialities'),
    path('specialities/<int:pk>/', SpecialityView.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'}), name='speciality-detail'),

    path('curriculums/', CurriculumView.as_view({'get': 'list', 'post': 'create'}), name='curriculums'),
    path('curriculums/<int:pk>/', CurriculumView.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'}), name='curriculum-detail'),

    path('technologies/', TechnologyView.as_view({'get': 'list', 'post': 'create'}), name='technologies'),
    path('technologies/<int:pk>/', TechnologyView.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'}), name='technology-detail'),

    path('competencies/', CompetencyView.as_view({'get': 'list', 'post': 'create'}), name='competencies'),
    path('competencies/<int:pk>/', CompetencyView.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'}), name='competency-detail'),

    path('base_disciplines/', BaseDisciplineView.as_view({'get': 'list', 'post': 'create'}), name='base_disciplines'),
    path('base_disciplines/<int:pk>/', BaseDisciplineView.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'}), name='base_discipline-detail'),

    path('disciplines/', DisciplineView.as_view({'get': 'list', 'post': 'create'}), name='disciplines'),
    path('disciplines/<int:pk>/', DisciplineView.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'}), name='discipline-detail'),

    path('vacancies/', VacancyView.as_view({'get': 'list', 'post': 'create'}), name='vacancies'),
    path('vacancies/<int:pk>/', VacancyView.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'}), name='vacancy-detail'),

    path('acms/', ACMView.as_view({'get': 'list', 'post': 'create'}), name='acms'),
    path('acms/<int:pk>/', ACMView.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'}), name='acm-detail'),

    path('vcms/', VCMView.as_view({'get': 'list', 'post': 'create'}), name='vcms'),
    path('vcms/<int:pk>/', VCMView.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'}), name='vcm-detail'),

    path('ucms/', UCMView.as_view({'get': 'list', 'post': 'create'}), name='ucms'),
    path('ucms/<int:pk>/', UCMView.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'}), name='ucm-detail'),

    path('technologies/loadsampledata/', LoadSampleTechnologyData.as_view(), name='load-sample-technologies'),
    path('specialities/loadsampledata/', LoadSampleSpecialityData.as_view(), name='load-sample-specialities'),
    path('curriculums/loadsampledata/', LoadSampleCurriculumData.as_view(), name='load-sample-curriculums'),
    path('competencies/loadsampledata/', LoadSampleCompetencyData.as_view(), name='load-sample-competencies'),
    path('base_disciplines/loadsampledata/', LoadSampleBaseDisciplineData.as_view(), name='load-sample-base-disciplines'),
    path('disciplines/loadsampledata/', LoadSampleDisciplineData.as_view(), name='load-sample-disciplines'),
    path('vacancies/loadsampledata/', LoadSampleVacancyData.as_view(), name='load-sample-vacancies'),
    path('acms/loadsampledata/', LoadSampleACMData.as_view(), name='load-sample-acms'),
    path('vcms/loadsampledata/', LoadSampleVCMData.as_view(), name='load-sample-vcms'),
    path('ucms/loadsampledata/', LoadSampleUCMData.as_view(), name='load-sample-ucms'),

    # Relations endpoints
    path('relations/discipline-technology/', DisciplineTechnologyRelationView.as_view(), name='discipline-technology-relations'),
    path('relations/discipline-competency/', DisciplineCompetencyRelationView.as_view(), name='discipline-competency-relations'),
    path('relations/vacancy-technology/', VacancyTechnologyRelationView.as_view(), name='vacancy-technology-relations'),
    path('relations/vacancy-competency/', VacancyCompetencyRelationView.as_view(), name='vacancy-competency-relations'),
    path('relations/vcm-technology/', VCMTechnologyRelationView.as_view(), name='vcm-technology-relations'),
    path('relations/vcm-competency/', VCMCompetencyRelationView.as_view(), name='vcm-competency-relations'),

    # Маршруты для ImportHistory
    path('import_history/query/', ImportHistoryGetView.as_view(), name='import-history-get'),
    path('import_history/', ImportHistoryView.as_view({'get': 'list', 'post': 'create'}), name='import-history-list'),
    path('import_history/<int:pk>/', ImportHistoryView.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'}), name='import-history-detail'),
    
    # Маршруты для ImportStats
    path('import_stats/query/', ImportStatsGetView.as_view(), name='import-stats-get'),
    path('import_stats/', ImportStatsView.as_view({'get': 'list'}), name='import-stats-list'),
    path('import_stats/<int:pk>/', ImportStatsView.as_view({'get': 'retrieve', 'put': 'update'}), name='import-stats-detail'),

    # Маршруты для работы с Excel файлами
    path('upload-excel/', ExcelUploadView.as_view(), name='upload-excel'),
    path('process-excel/', ProcessExcelDataView.as_view(), name='process-excel'),
]