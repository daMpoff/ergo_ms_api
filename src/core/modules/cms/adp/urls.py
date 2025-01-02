from django.urls import (
    path
)

from rest_framework_simplejwt.views import (
    TokenRefreshView
)

from src.core.modules.cms.adp.views import (
    UserRegistrationValidationView,
    UserRegistrationView,
    UserAuthorizationView,
    SendConfirmationCodeView,
    VerifyConfirmationCodeView,
    ProtectedView
)

urlpatterns = [
    path('validate_registration/', UserRegistrationValidationView.as_view(), name='validate_registration'),
    path('registration/', UserRegistrationView.as_view(), name='registration'),
    path('authorization/', UserAuthorizationView.as_view(), name='authorization'),

    path('send_code/', SendConfirmationCodeView.as_view(), name="send_code"),
    path('verify_code/', VerifyConfirmationCodeView.as_view(), name="verify_code"),

    path('token_refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('protected/', ProtectedView.as_view(), name='protected'),
]