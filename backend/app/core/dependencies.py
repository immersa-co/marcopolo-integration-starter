from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status

from .config import Settings, get_settings
from ..services.chatbot import ChatStore, IntegrationDemoAgentService, get_chat_store as _get_chat_store
from ..services.auth import (
    AUTH_SESSION_ID_KEY,
    AuthPlatformService,
    UserSession,
    get_auth_session_store,
    user_session_from_auth_payload,
)
from ..services.platform import MarcoPoloService, SkillRegistry, load_skill_registry


def get_auth_service(settings: Settings = get_settings()) -> AuthPlatformService:
    return AuthPlatformService(settings)


def get_skill_registry(settings: Settings = get_settings()) -> SkillRegistry:
    return load_skill_registry(settings.skill_repo_path)


def get_current_session(request: Request) -> UserSession:
    auth_session_id = request.session.get(AUTH_SESSION_ID_KEY)
    return user_session_from_auth_payload(
        get_auth_session_store().get_for_request(request),
        auth_session_id=auth_session_id if isinstance(auth_session_id, str) else None,
    )


def require_authenticated_session(
    user_session: UserSession = Depends(get_current_session),
) -> UserSession:
    if not user_session.authenticated or user_session.user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sign in is required before calling MarcoPolo-backed routes.",
        )
    return user_session


def require_marcopolo_access(
    user_session: UserSession = Depends(get_current_session),
) -> UserSession:
    if not user_session.authenticated or user_session.user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sign in is required before calling MarcoPolo-backed routes.",
        )
    return user_session


def get_marcopolo_service(settings: Settings = get_settings()) -> MarcoPoloService:
    return MarcoPoloService(settings)


def get_chat_store() -> ChatStore:
    return _get_chat_store()


def get_agent_service(
    settings: Settings = Depends(get_settings),
    marcopolo: MarcoPoloService = Depends(get_marcopolo_service),
    skills: SkillRegistry = Depends(get_skill_registry),
) -> IntegrationDemoAgentService:
    return IntegrationDemoAgentService(settings, marcopolo, skills)
