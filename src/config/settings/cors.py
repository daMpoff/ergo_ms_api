from src.config.env import env

CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

BASE_BACKEND_URL = env.str(
    "DJANGO_BASE_BACKEND_URL",
    default="http://localhost:8000",
)