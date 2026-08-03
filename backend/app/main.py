from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from .api.auth import router as auth_router
from .api.chatbot import router as chat_router
from .api.configuration import router as config_router
from .api.connections import router as connections_router
from .api.integrations import router as integrations_router
from .core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    if not settings.session_secret:
        raise RuntimeError("SESSION_SECRET must be configured before starting the demo backend.")

    app = FastAPI(
        title="MarcoPolo Integration Demo API",
        version="0.2.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.session_secret,
        session_cookie=settings.session_cookie_name,
        max_age=settings.session_max_age_seconds,
        same_site="lax",
        https_only=settings.session_https_only,
    )

    app.include_router(config_router)
    app.include_router(auth_router)
    app.include_router(connections_router)
    app.include_router(integrations_router)
    app.include_router(chat_router)
    return app


app = create_app()
