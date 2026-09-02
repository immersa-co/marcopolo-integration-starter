"""Namespace-key to user-token exchange shared by auth and platform layers."""

from __future__ import annotations

import time
from dataclasses import dataclass

from marcopolo import MarcopoloNamespace
from marcopolo.errors import MarcopoloError

from ...core.config import Settings


class NamespaceTokenError(RuntimeError):
    def __init__(self, detail: str, status_code: int = 502):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


@dataclass(frozen=True)
class IssuedNamespaceUserToken:
    access_token: str
    expires_at: float
    namespace: str
    company: str
    email: str


async def issue_namespace_user_token(settings: Settings, email: str) -> IssuedNamespaceUserToken:
    """Exchange the configured namespace key for one end user's token."""
    key = settings.marcopolo_namespace_key.strip()
    if not key:
        raise NamespaceTokenError(
            "MARCOPOLO_NAMESPACE_KEY is not configured for namespace_key mode.",
            status_code=503,
        )
    normalized_email = (email or "").strip().lower()
    if not normalized_email:
        raise NamespaceTokenError("A demo user email is required.", status_code=401)

    try:
        async with MarcopoloNamespace(
            api_key=key,
            base_url=settings.marcopolo_web_base_url,
        ) as namespace_client:
            token = await namespace_client.issue_user_token(normalized_email)
    except MarcopoloError as exc:
        raise NamespaceTokenError(
            f"MarcoPolo namespace user-token exchange failed: {exc}",
            status_code=502,
        ) from exc

    return IssuedNamespaceUserToken(
        access_token=token.access_token,
        expires_at=time.time() + float(token.expires_in),
        namespace=token.namespace,
        company=token.tenant,
        email=token.email,
    )
