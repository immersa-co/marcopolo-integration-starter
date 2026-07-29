import unittest
from unittest.mock import patch

import httpx

from backend.app.config import Settings
from backend.app.services.auth import (
    AuthPlatformError,
    AuthPlatformService,
    _normalized_auth_payload_for_mode,
    _parse_marcopolo_bootstrap_response,
    user_session_from_auth_payload,
)
from backend.app.services.auth_session_store import get_auth_session_store


def _fake_async_client(responses: list[httpx.Response], requests: list[dict[str, object]]):
    class FakeAsyncClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def post(self, url, **kwargs):
            requests.append({"url": url, **kwargs})
            return responses.pop(0)

    return FakeAsyncClient


class FakeRequest:
    def __init__(self) -> None:
        self.session: dict[str, object] = {}
        self.query_params = {"state": "state", "code": "authorization-code"}


class AuthSessionContractTests(unittest.IsolatedAsyncioTestCase):
    def test_bootstrap_response_exposes_authoritative_identity(self) -> None:
        response = httpx.Response(
            200,
            json={
                "success": True,
                "data": {
                    "redirect_url": "/app/auth/callback#token",
                    "company": "entelligence-demo",
                    "namespace": "entelligence",
                },
            },
        )

        bootstrap = _parse_marcopolo_bootstrap_response(response)

        self.assertEqual(bootstrap.company, "entelligence-demo")
        self.assertEqual(bootstrap.namespace, "entelligence")
        self.assertEqual(bootstrap.redirect_url, "/app/auth/callback#token")

    def test_bootstrap_response_requires_all_identity_fields(self) -> None:
        response = httpx.Response(
            200,
            json={
                "success": True,
                "data": {
                    "redirect_url": "/app/auth/callback#token",
                    "company": "entelligence-demo",
                },
            },
        )

        with self.assertRaisesRegex(AuthPlatformError, "namespace"):
            _parse_marcopolo_bootstrap_response(response)

    def test_workos_token_without_successful_bootstrap_is_unprovisioned(self) -> None:
        payload = _normalized_auth_payload_for_mode(
            {
                "provider": "impersonation",
                "user": {
                    "subject": "impersonation:partner@example.com",
                    "email": "partner@example.com",
                },
                "marcopolo_access_token": "workos-access-token",
                "marcopolo_provisioned": False,
            },
            "workos_connect",
        )

        session = user_session_from_auth_payload(payload)

        self.assertFalse(session.marcopolo_provisioned)
        self.assertIsNone(session.marcopolo_access_token)
        self.assertIsNone(session.company)
        self.assertIsNone(session.namespace)

    async def test_code_exchange_bootstraps_and_persists_identity(self) -> None:
        request = FakeRequest()
        settings = Settings(
            session_secret="session-secret",
            workos_connect_auth_url="https://modern-berry-85-entelligence-integration.authkit.app",
            workos_connect_client_id="client_01KXM9J1GK2R79E2Q53CMAQTZF",
            workos_connect_client_secret="client-secret",
            workos_connect_redirect_uri="http://localhost:8001/api/auth/workos/callback",
            marcopolo_web_base_url="http://localhost:8000",
        )
        AuthPlatformService(settings).impersonate_user(request, "partner@example.com")
        request.session["workos_connect_state"] = "state"
        requests: list[dict[str, object]] = []
        responses = [
            httpx.Response(
                200,
                json={
                    "access_token": "workos-access-token",
                    "refresh_token": "workos-refresh-token",
                    "token_type": "Bearer",
                    "expires_in": 3600,
                },
            ),
            httpx.Response(
                200,
                json={
                    "success": True,
                    "data": {
                        "redirect_url": "/app/auth/callback#token",
                        "company": "entelligence-demo",
                        "namespace": "entelligence",
                    },
                },
            ),
        ]

        try:
            with patch(
                "backend.app.services.auth.httpx.AsyncClient",
                _fake_async_client(responses, requests),
            ):
                response = await AuthPlatformService(settings).complete_workos_connect(request)

            auth_payload = get_auth_session_store().get_for_request(request)
            self.assertEqual(response.status_code, 302)
            self.assertIsNotNone(auth_payload)
            self.assertTrue(auth_payload["marcopolo_provisioned"])
            self.assertEqual(auth_payload["company"], "entelligence-demo")
            self.assertEqual(auth_payload["namespace"], "entelligence")
            self.assertEqual(requests[1]["url"], "http://localhost:8000/api/auth/bootstrap")
            self.assertEqual(
                requests[1]["headers"]["Authorization"],
                "Bearer workos-access-token",
            )
            self.assertEqual(
                requests[1]["json"],
                {
                    "access_token": "workos-access-token",
                    "refresh_token": "workos-refresh-token",
                },
            )
        finally:
            get_auth_session_store().clear_for_request(request)

    async def test_bootstrap_failure_leaves_existing_session_unprovisioned(self) -> None:
        request = FakeRequest()
        settings = Settings(
            session_secret="session-secret",
            workos_connect_auth_url="https://modern-berry-85-entelligence-integration.authkit.app",
            workos_connect_client_id="client_01KXM9J1GK2R79E2Q53CMAQTZF",
            workos_connect_client_secret="client-secret",
            workos_connect_redirect_uri="http://localhost:8001/api/auth/workos/callback",
            marcopolo_web_base_url="http://localhost:8000",
        )
        AuthPlatformService(settings).impersonate_user(request, "partner@example.com")
        request.session["workos_connect_state"] = "state"
        requests: list[dict[str, object]] = []
        responses = [
            httpx.Response(200, json={"access_token": "workos-access-token"}),
            httpx.Response(502, json={"error": "namespace registry unavailable"}),
        ]

        try:
            with patch(
                "backend.app.services.auth.httpx.AsyncClient",
                _fake_async_client(responses, requests),
            ):
                with self.assertRaisesRegex(AuthPlatformError, "namespace registry unavailable"):
                    await AuthPlatformService(settings).complete_workos_connect(request)

            auth_payload = get_auth_session_store().get_for_request(request)
            self.assertIsNotNone(auth_payload)
            self.assertFalse(auth_payload["marcopolo_provisioned"])
            self.assertIsNone(auth_payload["marcopolo_access_token"])
            self.assertIsNone(auth_payload["company"])
            self.assertIsNone(auth_payload["namespace"])
        finally:
            get_auth_session_store().clear_for_request(request)


if __name__ == "__main__":
    unittest.main()
