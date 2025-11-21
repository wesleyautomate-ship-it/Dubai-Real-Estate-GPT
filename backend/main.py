"""
Dubai Real Estate Semantic Search API
Main FastAPI application
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from pathlib import Path

from backend.config import API_HOST, API_PORT
from backend.supabase_client import get_client, close_client, call_rpc
from backend.api import owners_api, search_api, properties_api, stats_api, chat_tools_api

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info("[startup] Starting Dubai Real Estate Search API...")
    logger.info(f"[startup] API available at http://{API_HOST}:{API_PORT}")
    
    # Initialize Supabase client
    await get_client()
    logger.info("[startup] Supabase client initialized")
    
    # Health check
    try:
        # Try to call db_stats if it exists
        stats = await call_rpc("db_stats", {})
        if stats:
            result = stats[0] if isinstance(stats, list) else stats
            logger.info(f"[startup] Database connected - {result.get('property_count', 0)} properties")
        else:
            logger.info("[startup] Database connected")
    except Exception as e:
        # db_stats function doesn't exist yet - that's okay
        logger.warning("[warning] db_stats function not found (run SQL in Supabase to create it)")
        logger.info("[startup] Server starting - basic functionality available")
    
    yield
    
    # Shutdown
    logger.info("[shutdown] Shutting down...")
    await close_client()
    logger.info("[shutdown] Cleanup complete")


# Create FastAPI app
app = FastAPI(
    title="Dubai Real Estate Semantic Search API",
    description="Natural language property search with OpenAI embeddings and Supabase pgvector",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan
)

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for dev (restrict in production)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(search_api.router, prefix="/api", tags=["Search"])
app.include_router(properties_api.router, prefix="/api", tags=["Properties"])
app.include_router(stats_api.router, prefix="/api", tags=["Statistics"])
app.include_router(owners_api.router, prefix="/api", tags=["Owners"])
app.include_router(chat_tools_api.router, prefix="/api", tags=["Chat Tools"])

# Mount frontend static files
frontend_path = Path(__file__).parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")
    
    @app.get("/")
    async def serve_frontend():
        """Serve frontend HTML"""
        index_path = frontend_path / "index.html"
        if index_path.exists():
            return FileResponse(index_path)
        return {"message": "Frontend not found. Please build the frontend first."}
else:
    @app.get("/")
    async def root():
        return {
            "message": "Dubai Real Estate Semantic Search API",
            "version": "1.0.0",
            "docs": "/api/docs",
            "chat": "/chat",
            "endpoints": {
                "search": "/api/search?q=your+query",
                "property": "/api/properties/{id}",
                "stats": "/api/stats"
            }
        }


@app.get("/chat")
async def serve_chat():
    """Serve chat interface"""
    chat_path = frontend_path / "chat.html"
    if chat_path.exists():
        return FileResponse(chat_path)
    return {"message": "Chat interface not found. Please ensure frontend/chat.html exists."}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Try db_stats first
        try:
            stats = await call_rpc("db_stats", {})
            return {
                "status": "healthy",
                "database": "connected",
                "stats": stats[0] if stats else None
            }
        except:
            # Fallback to simple check
            client = await get_client()
            result = await client.table('properties').select('id', count='exact').limit(1).execute()
            return {
                "status": "healthy",
                "database": "connected",
                "note": "db_stats function not available, using basic check",
                "properties_count": result.count if hasattr(result, 'count') else "unknown"
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "error",
            "error": str(e)
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=API_HOST,
        port=API_PORT,
        reload=True
    )
