"""
Django settings for annapurna_pro project.

All configurations are unified here, including CRM features, AI calling integrations,
REST Framework, Celery, Channels, CORS, and Third-Party API integrations.
"""

import os
from datetime import timedelta
from pathlib import Path
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file
load_dotenv(BASE_DIR / ".env")

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "django-insecure-iv-1a0a@v_j*bt24288c6apavp7!fui$ms)z6jx!*2cdrr+=hl")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get("DJANGO_DEBUG", "true").lower() == "true"

ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "*").split(",")

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party packages
    "rest_framework",
    "rest_framework.authtoken",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "django_filters",
    "corsheaders",
    "drf_spectacular",
    "channels",
    # Single Consolidated Local App
    "myapp",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "myapp.middleware.AuditLogMiddleware",
]

ROOT_URLCONF = "annapurna_pro.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "annapurna_pro.wsgi.application"
ASGI_APPLICATION = "annapurna_pro.asgi.application"

AUTH_USER_MODEL = "myapp.User"

# Database
# Defaults to SQLite; switch to PostgreSQL by setting DATABASE_ENGINE=postgres
# if os.environ.get("DATABASE_ENGINE", "sqlite") == "postgres":
#     DATABASES = {
#         "default": {
#             "ENGINE": "django.db.backends.postgresql",
#             "NAME": os.environ.get("POSTGRES_DB", "anpurna_properties"),
#             "USER": os.environ.get("POSTGRES_USER", "anpurna_properties"),
#             "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "anpurna_properties"),
#             "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
#             "PORT": os.environ.get("POSTGRES_PORT", "5432"),
#         }
#     }
# else:
#     DATABASES = {
#         "default": {
#             "ENGINE": "django.db.backends.sqlite3",
#             "NAME": BASE_DIR / "db.sqlite3",
#         }
#     }
DATABASES = {
    'default': {
        'ENGINE': "django.db.backends.postgresql",
        'NAME': 'annapurna',
        'USER': 'postgres',
        'PASSWORD': 'rahul',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- DRF Configuration ----------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "myapp.pagination.StandardPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.ScopedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "webhooks": "120/min",
        "whatsapp-send": "60/min",
    },
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "myapp.exceptions.api_exception_handler",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=20),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer", "JWT"),
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Annapurna Pro — AI Calling CRM API",
    "DESCRIPTION": "Annapurna Pro real-estate AI calling and CRM lead automation backend.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

CORS_ALLOWED_ORIGINS = os.environ.get(
    "CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000"
).split(",")

# --- Celery Configuration -------------------------------------------------
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
CELERY_TASK_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_ALWAYS_EAGER = os.environ.get("CELERY_TASK_ALWAYS_EAGER", "true").lower() == "true"
CELERY_TASK_EAGER_PROPAGATES = True

# --- Integrations (Exotel / ElevenLabs / WhatsApp / LLM) ------------------
AI_CALLING_MOCK_PROVIDERS = os.environ.get("AI_CALLING_MOCK_PROVIDERS", "true").lower() == "true"

EXOTEL_SID = os.environ.get("EXOTEL_SID", "")
EXOTEL_API_KEY = os.environ.get("EXOTEL_API_KEY", "")
EXOTEL_API_TOKEN = os.environ.get("EXOTEL_API_TOKEN", "")
EXOTEL_CALLER_ID = os.environ.get("EXOTEL_CALLER_ID", "")
EXOTEL_WEBHOOK_SECRET = os.environ.get("EXOTEL_WEBHOOK_SECRET", "")

ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
ELEVENLABS_AGENT_ID = os.environ.get("ELEVENLABS_AGENT_ID", "")

LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "openai")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
LLM_MODEL = os.environ.get("LLM_MODEL", "gpt-5.6-luna")
LLM_API_BASE_URL = os.environ.get("LLM_API_BASE_URL", "https://api.openai.com/v1")

WHATSAPP_PHONE_NUMBER_ID = os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "")
WHATSAPP_ACCESS_TOKEN = os.environ.get("WHATSAPP_ACCESS_TOKEN", "")
WHATSAPP_VERIFY_TOKEN = os.environ.get("WHATSAPP_VERIFY_TOKEN", "dev-verify-token")
WHATSAPP_TEMPLATE_NAME = os.environ.get("WHATSAPP_TEMPLATE_NAME", "enquiry_ack_v1")
WHATSAPP_TEMPLATE_LANG = os.environ.get("WHATSAPP_TEMPLATE_LANG", "hi")
WHATSAPP_APP_SECRET = os.environ.get("WHATSAPP_APP_SECRET", "")
WHATSAPP_GRAPH_VERSION = os.environ.get("WHATSAPP_GRAPH_VERSION", "v23.0")

EXOTEL_API_BASE_URL = os.environ.get("EXOTEL_API_BASE_URL", "https://api.in.exotel.com")
EXOTEL_STREAM_URL = os.environ.get("EXOTEL_STREAM_URL", "")
EXOTEL_STATUS_CALLBACK_URL = os.environ.get("EXOTEL_STATUS_CALLBACK_URL", "")
EXOTEL_STREAM_SAMPLE_RATE = int(os.environ.get("EXOTEL_STREAM_SAMPLE_RATE", "16000"))

ELEVENLABS_API_BASE_URL = os.environ.get("ELEVENLABS_API_BASE_URL", "https://api.elevenlabs.io")
ELEVENLABS_WS_BASE_URL = os.environ.get("ELEVENLABS_WS_BASE_URL", "wss://api.elevenlabs.io")
PROVIDER_HTTP_TIMEOUT_SECONDS = float(os.environ.get("PROVIDER_HTTP_TIMEOUT_SECONDS", "15"))

AI_QUALIFICATION_MAX_CLARIFY_ATTEMPTS = 2

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "%(asctime)s %(levelname)s %(name)s: %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "annapurna_pro": {"handlers": ["console"], "level": "DEBUG", "propagate": False},
    },
}

# --- Email Configuration --------------------------------------------------
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = "noreply@annapurnapro.com"
