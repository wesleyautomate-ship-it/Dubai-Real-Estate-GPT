"""
API Module
Contains FastAPI routers for search, properties, and stats endpoints
"""

from . import owners_api, search_api, properties_api, stats_api

__all__ = ["owners_api", "search_api", "properties_api", "stats_api"]

"""backend/api package"""
