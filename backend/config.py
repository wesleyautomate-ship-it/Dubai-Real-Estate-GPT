"""
Backend Configuration
Loads environment variables for Supabase, OpenAI, and API settings.
"""

import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Supabase Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL")

# OpenAI / Gemini Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_CHAT_MODEL = os.getenv("GEMINI_CHAT_MODEL", "gemini-1.5-flash")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").strip().lower()

# API Configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8787"))

# Embedding Configuration
EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_DIMENSIONS = int(os.getenv("OPENAI_EMBEDDING_DIM", "1536"))

# Database Configuration
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))

# Validate required settings
if not SUPABASE_URL:
    raise ValueError("SUPABASE_URL not set in environment")
if not SUPABASE_SERVICE_ROLE_KEY:
    raise ValueError("SUPABASE_SERVICE_ROLE_KEY not set in environment")
if LLM_PROVIDER not in {"openai", "gemini"}:
    raise ValueError("LLM_PROVIDER must be either 'openai' or 'gemini'")
if LLM_PROVIDER == "gemini" and not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not set in environment")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not set in environment")
