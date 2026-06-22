"""
Django settings for the AI-Based RFP Authoring Tool (MVP vertical slice).

Defaults run instantly on SQLite with the offline LLM fallback so the demo
works with zero external dependencies. The proposal's production path
(PostgreSQL + pgvector, OpenAI) is enabled purely by env vars.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _bool(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-insecure-change-me")
DEBUG = _bool("DJANGO_DEBUG", "true")
ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
if DEBUG:
    ALLOWED_HOSTS.append("testserver")  # Django test client

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    # Project apps
    "apps.accounts",
    "apps.llm",
    "apps.knowledge",
    "apps.drafting",
    "apps.compliance",
    "apps.audit",
    "apps.exporting",
    "apps.review",
    "apps.similarity",
    "apps.observability",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.observability.middleware.MetricsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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

# ---- Database: SQLite by default; Postgres+pgvector for production ----
USE_PGVECTOR = _bool("USE_PGVECTOR", "false")
if os.getenv("DATABASE_URL"):
    import urllib.parse as _u

    _p = _u.urlparse(os.environ["DATABASE_URL"])
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": _p.path.lstrip("/"),
            "USER": _p.username,
            "PASSWORD": _p.password,
            "HOST": _p.hostname,
            "PORT": _p.port or 5432,
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = []
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.accounts.authentication.CsrfExemptSessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
}

# Dev: allow the Vite frontend.
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
CORS_ALLOW_CREDENTIALS = True

# ---- LLM gateway (provider-agnostic) ----
LLM = {
    "PROVIDER": os.getenv("LLM_PROVIDER", "mock"),
    "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", ""),
    "OPENAI_BASE_URL": os.getenv("OPENAI_BASE_URL", ""),
    "GENERATION_MODEL": os.getenv("OPENAI_GENERATION_MODEL", "gpt-4o"),
    "EMBEDDING_MODEL": os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
}

# ---- RFQ success metrics (§3.7) treated as acceptance thresholds ----
SUCCESS_METRICS = {
    "faithfulness": 0.95,
    "hallucination_max": 0.05,
    "citation_accuracy": 0.98,
    "context_recall": 0.90,
    "context_precision": 0.85,
    "gfr_compliance": 0.95,
    "structured_output": 0.98,
}
