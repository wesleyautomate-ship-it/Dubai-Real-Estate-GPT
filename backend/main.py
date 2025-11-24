"""
Dubai Real Estate Semantic Search API
Main FastAPI application
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
import structlog

from backend.api import (
    auth_api,
    conversations_api,
    owners_api,
    search_api,
    properties_api,
    stats_api,
    chat_tools_api,
    chat_endpoint,
)
from backend.api.common import ApiError, error_response
from backend.api.middleware import auth_middleware, request_context_middleware
from backend.config import (
    API_HOST,
    API_PORT,
    GEMINI_API_KEY,
    LLM_PROVIDER,
    OPENAI_API_KEY,
    NEON_SERVICE_ROLE_KEY,
)
from backend.logging_config import setup_logging
from backend.settings import get_settings
from backend.neon_client import close_client, get_client, call_rpc, health_check as neon_health_check

try:  # Optional tracing dependencies
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
except ImportError:  # pragma: no cover - tracing is optional
    trace = None  # type: ignore
    FastAPIInstrumentor = None  # type: ignore
    OTLPSpanExporter = None  # type: ignore
    TracerProvider = None  # type: ignore
    BatchSpanProcessor = None  # type: ignore
    ConsoleSpanExporter = None  # type: ignore
    Resource = None  # type: ignore


settings = get_settings()
setup_logging(settings.logging.level, settings.logging.json)
logger = structlog.get_logger(__name__)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


def _init_tracer(app: FastAPI) -> None:
    if not settings.tracing.enabled or trace is None or TracerProvider is None:
        logger.info("[tracing] OpenTelemetry disabled")
        return

    resource = Resource.create({"service.name": settings.tracing.service_name}) if Resource else None
    tracer_provider = TracerProvider(resource=resource)

    if settings.tracing.endpoint and OTLPSpanExporter is not None:
        tracer_provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.tracing.endpoint))
        )
    else:
        tracer_provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

    trace.set_tracer_provider(tracer_provider)

    if FastAPIInstrumentor is not None:
        FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer_provider)
        logger.info("[tracing] OpenTelemetry instrumentation enabled")


def _init_metrics(app: FastAPI) -> None:
    if not settings.metrics.enabled:
        logger.info("[metrics] Prometheus instrumentation disabled")
        return

    Instrumentator().instrument(app).expose(app, endpoint=settings.metrics.endpoint)
    logger.info("[metrics] Prometheus instrumentation enabled", endpoint=settings.metrics.endpoint)


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

# Instrumentation
_init_tracer(app)
_init_metrics(app)

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# Middleware & exception handlers
app.middleware("http")(auth_middleware)
app.middleware("http")(request_context_middleware)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail
    if isinstance(detail, dict):
        code = str(detail.get("code", "http_error"))
        message = str(detail.get("message", "Request failed."))
        details = detail.get("details")
    else:
        code = "http_error"
        message = str(detail) if detail else exc.__class__.__name__
        details = detail if detail and not isinstance(detail, str) else None

    return error_response(
        request,
        status_code=exc.status_code,
        error=ApiError(code=code, message=message, details=details),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return error_response(
        request,
        status_code=422,
        error=ApiError(
            code="validation_error",
            message="Invalid request payload.",
            details=exc.errors(),
        ),
    )

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
app.include_router(conversations_api.router, prefix="/api", tags=["Conversations"])
app.include_router(chat_tools_api.router, prefix="/api", tags=["Chat Tools"])
app.include_router(chat_endpoint.router, prefix="/api", tags=["Chat"])
app.include_router(auth_api.router, prefix="/api", tags=["Auth"])

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
    """Aggregated application health status."""

    checks = {
        "status": "healthy",
        "database": {},
        "llm": {},
        "background_jobs": {},
        "metrics": {"enabled": settings.metrics.enabled},
        "tracing": {"enabled": settings.tracing.enabled},
    }

    # Supabase health
    try:
        neon_ok = await neon_health_check()
        checks["database"].update({"neon_rest": "connected" if neon_ok else "error"})
    except Exception as exc:
        checks["database"].update({"neon_rest": f"error: {exc}"})
        checks["status"] = "degraded"

    try:
        stats = await call_rpc("db_stats", {})
        if stats:
            checks["database"].update({"stats": stats[0] if isinstance(stats, list) else stats})
    except Exception as exc:
        checks["database"].update({"stats_error": str(exc)})

    # LLM provider health
    llm_provider = settings.llm.provider
    if llm_provider == "openai":
        checks["llm"].update({"provider": "openai", "api_key_present": bool(settings.llm.openai_api_key)})
        if not settings.llm.openai_api_key:
            checks["status"] = "degraded"
    elif llm_provider == "gemini":
        checks["llm"].update({"provider": "gemini", "api_key_present": bool(settings.llm.gemini_api_key)})
        if not settings.llm.gemini_api_key:
            checks["status"] = "degraded"

    # Background jobs (placeholder)
    if settings.metrics.enabled:
        checks["background_jobs"].update({"scheduler": "not_implemented"})

    return checks


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=API_HOST,
        port=API_PORT,
        reload=True
    )
