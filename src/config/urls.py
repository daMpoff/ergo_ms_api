from django.urls import (
    include, 
    path
)

from src.config.auto_config import discover_installed_app_urls
from src.config.settings.apps import EXTERNAL_MODULES_DIR

urlpatterns = [
    path("cms/adp/", include("src.core.modules.cms.adp.urls")),
    path("cms/content_manager/", include("src.core.modules.cms.content_manager.urls")),
    path("messenger/", include("src.core.modules.messenger.urls")),

    path("standard_functions/", include("src.core.standard_functions.urls")),
]

urlpatterns += discover_installed_app_urls(EXTERNAL_MODULES_DIR)