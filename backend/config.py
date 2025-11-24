"""
Backend Configuration
Loads environment variables for Neon REST, OpenAI, and API settings.
"""

from backend.settings import get_settings

settings = get_settings()

# API Configuration
API_HOST = settings.api.host
API_PORT = settings.api.port

# Neon REST/PostgREST-style Configuration
NEON_REST_URL = settings.neon_rest.url
NEON_SERVICE_ROLE_KEY = settings.neon_rest.service_role_key

# Database Configuration
NEON_DB_URL = settings.database.neon_db_url
FALLBACK_DB_URL = settings.database.fallback_db_url
# Primary DB URL to be used by the application
DB_URL = settings.database.primary_db_url
DB_POOL_SIZE = settings.database.pool_size

# OpenAI / Gemini Configuration
LLM_PROVIDER = settings.llm.provider
OPENAI_API_KEY = settings.llm.openai_api_key
OPENAI_CHAT_MODEL = settings.llm.openai_chat_model
GEMINI_API_KEY = settings.llm.gemini_api_key
GEMINI_CHAT_MODEL = settings.llm.gemini_chat_model

# Embedding Configuration
EMBEDDING_MODEL = settings.embedding.model
EMBEDDING_DIMENSIONS = settings.embedding.dimensions

# Logging / Metrics / Tracing
LOG_LEVEL = settings.logging.level
LOG_JSON = settings.logging.json
METRICS_ENABLED = settings.metrics.enabled
METRICS_ENDPOINT = settings.metrics.endpoint
OTEL_ENABLED = settings.tracing.enabled
OTEL_ENDPOINT = settings.tracing.endpoint
OTEL_SERVICE_NAME = settings.tracing.service_name

# Validate required settings
if not NEON_REST_URL:
    raise ValueError("NEON_REST_URL (or SUPABASE_URL) not set in environment")
if not NEON_SERVICE_ROLE_KEY:
    raise ValueError("NEON_SERVICE_ROLE_KEY (or SUPABASE_SERVICE_ROLE_KEY) not set in environment")
if LLM_PROVIDER not in {"openai", "gemini"}:
    raise ValueError("LLM_PROVIDER must be either 'openai' or 'gemini'")
if LLM_PROVIDER == "gemini":
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not set in environment")
if LLM_PROVIDER == "openai":
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not set in environment")
