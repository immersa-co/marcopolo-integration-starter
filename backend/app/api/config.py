from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from ..config import Settings, get_settings
from ..dependencies import get_auth_service, get_skill_registry
from ..marcopolo_auth_modes import get_auth_mode_definition, is_auth_mode_configured, list_auth_mode_definitions
from ..models import (
    PublicConfigResponse,
    PublicMarcoPoloAuthModeOption,
    RuntimeSkillSummary,
)
from ..services.auth import AuthPlatformService
from ..services.skills import SkillRegistry

router = APIRouter(prefix="/api", tags=["config"])


@router.get("/health")
async def healthcheck(
    auth_service: AuthPlatformService = Depends(get_auth_service),
    skill_registry: SkillRegistry = Depends(get_skill_registry),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    return {
        "status": "ok",
        "app_env": settings.app_env,
        "services": {
            "frontend": "expected",
            "backend": "ready",
            "auth": "configured" if auth_service.is_configured else "not_configured",
            "skills": skill_registry.count,
        },
    }


@router.get("/config/public", response_model=PublicConfigResponse)
async def public_config(
    request: Request,
    settings: Settings = Depends(get_settings),
    auth_service: AuthPlatformService = Depends(get_auth_service),
    skill_registry: SkillRegistry = Depends(get_skill_registry),
) -> PublicConfigResponse:
    auth_mode = auth_service.selected_marcopolo_auth_mode(request)
    auth_mode_definition = get_auth_mode_definition(auth_mode)
    return PublicConfigResponse(
        app_env=settings.app_env,
        auth={
            "required": settings.auth_required,
            "configured": auth_service.is_configured,
        },
        marco_polo={
            "mcp_url": settings.marcopolo_mcp_url,
            "api_base_url": settings.marcopolo_api_base_url,
            "web_base_url": settings.marcopolo_web_base_url,
            "auth_mode": auth_mode,
            "auth_mode_label": auth_mode_definition.label if auth_mode_definition else auth_mode,
            "auth_mode_description": (
                auth_mode_definition.description
                if auth_mode_definition
                else "Unknown MarcoPolo auth mode. Check the available auth mode registry."
            ),
            "auth_mode_configured": is_auth_mode_configured(settings, auth_mode),
            "browser_bootstrap_path": settings.marcopolo_browser_bootstrap_path,
            "browser_bootstrap_redirect": settings.marcopolo_browser_bootstrap_redirect,
            "available_auth_modes": [
                PublicMarcoPoloAuthModeOption(
                    key=definition.key,
                    label=definition.label,
                    description=definition.description,
                    implemented=definition.implemented,
                    configured=is_auth_mode_configured(settings, definition.key),
                    required_env_vars=list(definition.required_env_vars),
                )
                for definition in list_auth_mode_definitions()
            ],
        },
        llm={
            "provider": settings.llm_provider,
            "model": settings.llm_model,
            "api_base_url": settings.llm_api_base_url,
            "api_key_configured": bool(settings.llm_api_key),
        },
        skills=[
            RuntimeSkillSummary(
                name=skill.name,
                description=skill.description,
            )
            for skill in skill_registry.summaries()
        ],
    )
