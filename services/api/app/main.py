from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import Settings, get_settings
from app.core.errors import install_error_handlers
from app.dependencies import AppContainer
from app.modules.analyses.controller import router as analyses_router
from app.modules.health.controller import router as health_router


def create_app(settings: Settings | None = None) -> FastAPI:
    active_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        application.state.container = AppContainer.build(active_settings)
        try:
            yield
        finally:
            await application.state.container.close()

    application = FastAPI(
        title="VeriShield AI API",
        version="0.1.0",
        description="Multimodal verification intake and analysis orchestration.",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=active_settings.web_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Accept", "Content-Type"],
    )
    application.include_router(health_router, prefix=active_settings.api_prefix)
    application.include_router(analyses_router, prefix=active_settings.api_prefix)
    install_error_handlers(application)
    return application


app = create_app()
