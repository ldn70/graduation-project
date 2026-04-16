"""Django settings for the graduation project backend."""
from pathlib import Path
import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    "dev-secret-key-change-me-please-use-at-least-32-characters",
)
DEBUG = os.getenv("DJANGO_DEBUG", "true").lower() == "true"
ALLOWED_HOSTS = [host.strip() for host in os.getenv("DJANGO_ALLOWED_HOSTS", "*").split(",") if host.strip()]

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'rest_framework',
    'rest_framework_simplejwt.token_blacklist',
    'users',
    'jobs',
    'resumes',
    'core',
    'analysis',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


if os.getenv("DB_ENGINE", "sqlite").lower() == "mysql":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": os.getenv("DB_NAME", "graduation_project"),
            "USER": os.getenv("DB_USER", "root"),
            "PASSWORD": os.getenv("DB_PASSWORD", ""),
            "HOST": os.getenv("DB_HOST", "127.0.0.1"),
            "PORT": os.getenv("DB_PORT", "3306"),
            "OPTIONS": {"charset": "utf8mb4"},
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }


AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'zh-hans'
TIME_ZONE = 'Asia/Shanghai'

USE_I18N = True

USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

CORS_ALLOW_ALL_ORIGINS = os.getenv("CORS_ALLOW_ALL", "true").lower() == "true"
CORS_ALLOWED_ORIGINS = [
    origin.strip() for origin in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",") if origin.strip()
]

AUTH_USER_MODEL = "users.User"

def _env_rate(name, default):
    value = os.getenv(name, default)
    return value.strip() if isinstance(value, str) else default


def _env_int(name, default):
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


AUTH_LOGIN_FAIL_LIMIT_USERNAME = _env_int("AUTH_LOGIN_FAIL_LIMIT_USERNAME", 5)
AUTH_LOGIN_FAIL_LIMIT_IP = _env_int("AUTH_LOGIN_FAIL_LIMIT_IP", 20)
AUTH_LOGIN_LOCK_SECONDS = _env_int("AUTH_LOGIN_LOCK_SECONDS", 600)
AUTH_LOGIN_FAILURE_WINDOW_SECONDS = _env_int(
    "AUTH_LOGIN_FAILURE_WINDOW_SECONDS",
    AUTH_LOGIN_LOCK_SECONDS,
)


REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.ScopedRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": _env_rate("DRF_THROTTLE_ANON_RATE", "120/min"),
        "user": _env_rate("DRF_THROTTLE_USER_RATE", "300/min"),
        "auth_register": _env_rate("DRF_THROTTLE_AUTH_REGISTER_RATE", "10/min"),
        "auth_login": _env_rate("DRF_THROTTLE_AUTH_LOGIN_RATE", "20/min"),
        "jobs_search": _env_rate("DRF_THROTTLE_JOBS_SEARCH_RATE", "180/min"),
        "analysis_recommend": _env_rate("DRF_THROTTLE_ANALYSIS_RECOMMEND_RATE", "120/min"),
        "analysis_skill_demand": _env_rate("DRF_THROTTLE_ANALYSIS_SKILL_DEMAND_RATE", "150/min"),
        "analysis_skill_match": _env_rate("DRF_THROTTLE_ANALYSIS_SKILL_MATCH_RATE", "120/min"),
        "analysis_salary_predict": _env_rate("DRF_THROTTLE_ANALYSIS_SALARY_PREDICT_RATE", "90/min"),
        "analysis_trends": _env_rate("DRF_THROTTLE_ANALYSIS_TRENDS_RATE", "120/min"),
        "resume_generate": _env_rate("DRF_THROTTLE_RESUME_GENERATE_RATE", "30/min"),
        "resume_download": _env_rate("DRF_THROTTLE_RESUME_DOWNLOAD_RATE", "180/min"),
        "auth_security_logs": _env_rate("DRF_THROTTLE_AUTH_SECURITY_LOGS_RATE", "60/min"),
        "auth_security_logs_export": _env_rate("DRF_THROTTLE_AUTH_SECURITY_LOGS_EXPORT_RATE", "20/min"),
    },
    "EXCEPTION_HANDLER": "core.exceptions.api_exception_handler",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=2),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
