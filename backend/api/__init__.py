"""
API Module
Contains FastAPI routers for search, properties, and stats endpoints
"""

from . import (
    auth_api,
    conversations_api,
    owners_api,
    search_api,
    properties_api,
    stats_api,
    chat_endpoint,
    chat_tools_api,
)

__all__ = [
    "auth_api",
    "conversations_api",
    "owners_api",
    "search_api",
    "properties_api",
    "stats_api",
    "chat_endpoint",
    "chat_tools_api",
]

"""backend/api package"""
