"""ForecastGuard FastAPI Main Application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.api.health import router as health_router
from backend.app.config import settings


def create_app() -> FastAPI:
    """Application factory for ForecastGuard backend."""
    application = FastAPI(
        title="ForecastGuard API",
        description=(
            "AI-based forecast reliability intelligence system for medium-range "
            "numerical weather prediction (NWP)."
        ),
        version=settings.version,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Configure CORS middleware
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register API routers
    application.include_router(
        health_router,
        prefix=settings.api_v1_prefix,
    )

    return application


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.app.main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=True,
    )
