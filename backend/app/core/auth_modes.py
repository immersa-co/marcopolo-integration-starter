from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .config import Settings


@dataclass(frozen=True)
class MarcoPoloAuthModeDefinition:
    """Describes one supported or planned MarcoPolo integration mode.

    The demo exposes these definitions through the public config endpoint so a
    reviewer can understand:
    - which mode is currently selected
    - which secrets are required for that mode
    - whether the mode is implemented today or only tracked as a placeholder
    """

    key: str
    label: str
    description: str
    required_env_vars: tuple[str, ...]
    implemented: bool


MARCOPOLO_AUTH_MODES: dict[str, MarcoPoloAuthModeDefinition] = {
    "workos_connect": MarcoPoloAuthModeDefinition(
        key="workos_connect",
        label="WorkOS Standalone Connect (recommended)",
        description=(
            "Recommended partner flow: start with a user authenticated by your application, "
            "complete WorkOS Standalone Connect, then use MarcoPolo's issuer-resolved "
            "namespace and company."
        ),
        required_env_vars=(
            "WORKOS_CONNECT_AUTH_URL",
            "WORKOS_API_KEY",
            "WORKOS_CONNECT_CLIENT_ID",
            "WORKOS_CONNECT_CLIENT_SECRET",
            "WORKOS_CONNECT_REDIRECT_URI",
        ),
        implemented=True,
    ),
    "developer_api_token": MarcoPoloAuthModeDefinition(
        key="developer_api_token",
        label="Developer API Token (local shortcut)",
        description=(
            "Local-only shortcut for an already provisioned MarcoPolo workspace. "
            "This is not the partner integration authorization path."
        ),
        required_env_vars=("MARCOPOLO_DEVELOPER_API_TOKEN",),
        implemented=True,
    ),
}


def get_auth_mode_definition(mode: str) -> MarcoPoloAuthModeDefinition | None:
    return MARCOPOLO_AUTH_MODES.get(mode)


def list_auth_mode_definitions() -> list[MarcoPoloAuthModeDefinition]:
    return list(MARCOPOLO_AUTH_MODES.values())


def is_auth_mode_configured(settings: Settings, mode: str) -> bool:
    if mode == "developer_api_token":
        return bool(settings.marcopolo_developer_api_token.strip())
    if mode == "workos_connect":
        return settings.workos_connect_configured
    return False
