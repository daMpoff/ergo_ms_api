from django.urls import (
    include, 
    path
)

urlpatterns = [
    path("cms/adp/", include("src.core.modules.cms.adp.urls")),
    path("cms/content_manager/", include("src.core.modules.cms.content_manager.urls")),
    path("messenger/", include("src.core.modules.messenger.urls")),

    path("standard_functions/", include("src.core.standard_functions.urls")),

    path("external_modules/bi/", include("src.external_modules.bi.urls")),
    path("external_modules/bpm/", include("src.external_modules.bpm.urls")),
    path("external_modules/crm/", include("src.external_modules.crm.urls")),
    path("external_modules/hcm/", include("src.external_modules.hcm.urls")),
    path("external_modules/kms/", include("src.external_modules.kms.urls")),
    path("external_modules/lms/", include("src.external_modules.lms.urls")),
    path("external_modules/sis/", include("src.external_modules.sis.urls")),
]