from django.urls import path

from src.modules.cities_expansion.views import CitiesView , CountriesView, CountryCodesView, BoundingBoxesView, GetMyGroups, GetFile, DeleteGroup, GetMyTasks

urlpatterns = [
    path('cities/', CitiesView.as_view(), name='cities'),
    path('countries/', CountriesView.as_view(), name='countries'),
    path('country_codes/', CountryCodesView.as_view(), name='country_codes'),
    path('bounding_boxes/', BoundingBoxesView.as_view(), name='bounding_boxes'),
    path('get_my_groups/', GetMyGroups.as_view(), name='get_my_groups'),
    path('get_file/', GetFile.as_view(), name='get_file'),
    path('delete_group/<int:group_id>', DeleteGroup.as_view(), name='delete_group'),
    path('get_my_tasks/', GetMyTasks.as_view(), name='get_my_tasks')
]