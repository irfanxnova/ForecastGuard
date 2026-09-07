"""ForecastGuard FastAPI Main Application."""

import logging
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.api.health import router as health_router
from backend.app.api.historical import router as historical_router
from backend.app.api.inference import router as inference_router
from backend.app.config import settings

logger = logging.getLogger("forecastguard.api")


def create_app() -> FastAPI:
    """Application factory for ForecastGuard backend."""
    application = FastAPI(
        title="ForecastGuard API",
        description=(
            "AI-based forecast reliability intelligence system for medium-range "
            "numerical weather prediction (NWP) - SIH 2026 Problem Statement SIH26079."
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
    application.include_router(health_router)
    application.include_router(
        health_router,
        prefix=settings.api_v1_prefix,
    )
    application.include_router(
        inference_router,
        prefix=settings.api_v1_prefix,
    )
    application.include_router(
        historical_router,
        prefix=settings.api_v1_prefix,
    )

    # Optional static asset serving for production deployment
    from pathlib import Path
    dist_dir = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
    if dist_dir.exists():
        from fastapi.responses import FileResponse
        from fastapi.staticfiles import StaticFiles

        assets_dir = dist_dir / "assets"
        if assets_dir.exists():
            application.mount(
                "/assets",
                StaticFiles(directory=str(assets_dir)),
                name="static_assets",
            )

        index_file = dist_dir / "index.html"
        if index_file.exists():
            @application.get("/", include_in_schema=False)
            async def serve_spa_root():
                return FileResponse(str(index_file))

            @application.get("/index.html", include_in_schema=False)
            async def serve_spa_index():
                return FileResponse(str(index_file))

    # Hardened error handling: Structured errors with zero secret or stack trace leakage
    @application.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        clean_errors = []
        for err in exc.errors():
            clean_errors.append({
                "loc": [str(x) for x in err.get("loc", [])],
                "msg": str(err.get("msg", "")),
                "type": str(err.get("type", "")),
            })
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "Validation Error",
                "detail": clean_errors,
                "status_code": 422,
            },
        )

    @application.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled server error at {request.url.path}: {exc}", exc_info=False)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal Server Error",
                "detail": "An unexpected error occurred while processing the request. Details logged safely.",
                "status_code": 500,
            },
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
