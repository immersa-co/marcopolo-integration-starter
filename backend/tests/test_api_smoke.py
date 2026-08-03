import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from langchain_core.messages import ToolMessage

from backend.app.services.ai_agent.connection_matching import match_visible_connection
from backend.app.services.ai_agent.response_parser import (
    extract_preview_rows,
    extract_tool_error,
    normalize_tool_payload,
    parse_tool_message_payload,
)
from backend.app.services.marcopolo import (
    _DATA_CONNECTION_OPERATION_SPEC_INDEX,
    _select_operation_connection,
)
from backend.app.services.auth import AuthPlatformError, validate_marcopolo_email_identity
from backend.app.main import app
from backend.app.models import ConnectionListItem, UserProfile


class ApiSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def test_health_endpoint_returns_ok(self) -> None:
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "ok")
        self.assertIn("skills", payload["services"])

    def test_public_config_returns_runtime_shape(self) -> None:
        response = self.client.get("/api/config/public")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["appEnv"], "development")
        self.assertIn("auth", payload)
        self.assertIn("required", payload["auth"])
        self.assertIn("configured", payload["auth"])
        self.assertIn("marcoPolo", payload)
        self.assertIn("authMode", payload["marcoPolo"])
        self.assertIn("authModeLabel", payload["marcoPolo"])
        self.assertIn("authModeDescription", payload["marcoPolo"])
        self.assertIn("authModeConfigured", payload["marcoPolo"])
        self.assertIn("webBaseUrl", payload["marcoPolo"])
        self.assertIn("browserBootstrapPath", payload["marcoPolo"])
        self.assertIn("browserBootstrapRedirect", payload["marcoPolo"])
        self.assertIsInstance(payload["marcoPolo"]["availableAuthModes"], list)
        self.assertIn("llm", payload)
        self.assertIsInstance(payload["skills"], list)

    def test_auth_session_and_examples_match_runtime_configuration(self) -> None:
        session_response = self.client.get("/api/auth/session")
        self.assertEqual(session_response.status_code, 200)
        session_payload = session_response.json()
        self.assertIn("marcoPoloConfigured", session_payload)
        self.assertIn("marcoPoloProvisioned", session_payload)

        examples_response = self.client.get("/api/integrations/examples")
        self.assertEqual(examples_response.status_code, 200)
        self.assertEqual(len(examples_response.json()["examples"]), 3)

    def test_impersonate_route_creates_demo_session(self) -> None:
        response = self.client.post("/api/auth/impersonate", json={"email": "demo.user@example.com"})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["authenticated"])
        self.assertEqual(payload["provider"], "impersonation")
        self.assertEqual(payload["user"]["email"], "demo.user@example.com")

        session_payload = self.client.get("/api/auth/session").json()
        self.assertTrue(session_payload["authenticated"])
        self.assertEqual(session_payload["provider"], "impersonation")
        self.assertEqual(session_payload["user"]["email"], "demo.user@example.com")

        logout_response = self.client.post("/api/auth/logout")
        self.assertEqual(logout_response.status_code, 200)

    def test_protected_routes_require_authentication(self) -> None:
        connections = self.client.get("/api/connections")
        self.assertEqual(connections.status_code, 401)

        embedded_setup = self.client.post(
            "/api/connections/setup/embedded",
            json={"connectionType": "jira"},
        )
        self.assertEqual(embedded_setup.status_code, 401)

        setup_session_status = self.client.get(
            "/api/connections/setup-session-status",
            params={"setupSessionId": "setup_test"},
        )
        self.assertEqual(setup_session_status.status_code, 401)

        setup_session_resume = self.client.get(
            "/api/connections/setup-session-resume",
            params={"setupSessionId": "setup_test"},
        )
        self.assertEqual(setup_session_resume.status_code, 401)

        setup_session_lookup = self.client.get(
            "/api/connections/setup-session-lookup",
            params={"hostSessionId": "host_test"},
        )
        self.assertEqual(setup_session_lookup.status_code, 401)

        chat = self.client.post("/api/chat", json={"message": "hello"})
        self.assertEqual(chat.status_code, 401)

        integration_run = self.client.post("/api/integrations/run", json={"exampleId": "jira_open_tickets"})
        self.assertEqual(integration_run.status_code, 401)

        marcopolo_authorize = self.client.get("/api/auth/marcopolo/authorize", follow_redirects=False)
        self.assertEqual(marcopolo_authorize.status_code, 401)

    def test_ext_app_proxy_preserves_single_api_prefix(self) -> None:
        captured: dict[str, object] = {}

        class FakeUpstreamResponse:
            status_code = 200
            headers = {"content-type": "application/json"}
            content = b'{"ok":true}'

        class FakeAsyncClient:
            def __init__(self, *args, **kwargs) -> None:
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb) -> None:
                return None

            async def request(self, method, url, params=None, headers=None, content=None):
                captured["method"] = method
                captured["url"] = url
                captured["params"] = dict(params or {})
                captured["headers"] = dict(headers or {})
                captured["content"] = content
                return FakeUpstreamResponse()

        with patch("backend.app.api.connections.httpx.AsyncClient", FakeAsyncClient):
            response = self.client.get(
                "/api/connections/ext-app-proxy/api/connections/types/?q=test",
                headers={"Authorization": "Bearer widget-token"},
            )

        self.assertEqual(response.status_code, 200)
        config = self.client.get("/api/config/public").json()
        self.assertEqual(
            captured["url"],
            f"{config['marcoPolo']['apiBaseUrl']}/connections/types/",
        )
        self.assertEqual(captured["method"], "GET")
        self.assertEqual(captured["params"], {"q": "test"})
        self.assertEqual(
            captured["headers"],
            {
                "Authorization": "Bearer widget-token",
                "Accept": "*/*",
            },
        )

    def test_connection_matcher_supports_non_demo_connectors(self) -> None:
        connections = [
            {
                "name": "jira-team",
                "displayName": "Jira",
                "type": "jira",
                "capabilities": ["query"],
            },
            {
                "name": "github-main",
                "displayName": "GitHub",
                "type": "github",
                "capabilities": ["query"],
            },
        ]

        selected = match_visible_connection(
            "List open Jira issues assigned to me this sprint.",
            connections,
        )

        self.assertIsNotNone(selected)
        self.assertEqual(selected["type"], "jira")

    def test_connection_matcher_prefers_named_connection_over_generic_query_terms(self) -> None:
        connections = [
            {
                "name": "salesforce-prod",
                "displayName": "Salesforce",
                "type": "salesforce",
                "capabilities": ["query"],
            },
            {
                "name": "jira-team",
                "displayName": "Jira",
                "type": "jira",
                "capabilities": ["query"],
            },
        ]

        selected = match_visible_connection(
            "In Jira, show the top issue counts by assignee.",
            connections,
        )

        self.assertIsNotNone(selected)
        self.assertEqual(selected["type"], "jira")

    def test_sdk_example_connection_selection_uses_runtime_name_match(self) -> None:
        salesforce_definition = _DATA_CONNECTION_OPERATION_SPEC_INDEX["salesforce_top_accounts"]
        connections = [
            ConnectionListItem(
                name="sfdc-prod-random-slug",
                displayName="Salesforce Prod",
                type="salesforce",
                capabilities=["query"],
            ),
            ConnectionListItem(
                name="other-connection",
                displayName="Other",
                type="postgres",
                capabilities=["query"],
            ),
        ]

        selected = _select_operation_connection(connections, salesforce_definition)

        self.assertIsNotNone(selected)
        self.assertEqual(selected.name, "sfdc-prod-random-slug")

    def test_extract_query_rows_supports_data_payload(self) -> None:
        rows = extract_preview_rows(
            {
                "success": True,
                "data": '[{"key":"JIRA-101","summary":"Broken sync"},{"key":"JIRA-102","summary":"Auth bug"}]',
                "preview": "[]",
            }
        )

        self.assertEqual(
            rows,
            [
                {"key": "JIRA-101", "summary": "Broken sync"},
                {"key": "JIRA-102", "summary": "Auth bug"},
            ],
        )

    def test_extract_shell_error_reads_structured_query_failure(self) -> None:
        message = extract_tool_error(
            {
                "success": False,
                "stdout": '{"success": false, "message": "Query execution failed: runtime missing"}',
                "stderr": "",
            }
        )

        self.assertEqual(message, "Query execution failed: runtime missing")

    def test_ai_agent_response_parser_normalizes_workspace_shell_stdout(self) -> None:
        payload = {
            "structuredContent": {
                "success": True,
                "exit_code": 0,
                "stdout": (
                    '{"success": true, "connections": ['
                    '{"name": "snowflake-prod", "type": "snowflake"}, '
                    '{"name": "github-main", "type": "github"}'
                    "], \"count\": 2}"
                ),
                "stderr": "",
            },
            "isError": False,
        }

        normalized = normalize_tool_payload(payload, tool_name="workspace_shell")

        self.assertEqual(normalized["success"], True)
        self.assertIn("stdout_parsed", normalized)
        self.assertEqual(normalized["stdout_parsed"]["count"], 2)

    def test_ai_agent_response_parser_extracts_workspace_shell_rows(self) -> None:
        message = ToolMessage(
            content='{"structuredContent":{"success":true,"exit_code":0,"stdout":"{\\"success\\": true, \\"connections\\": [{\\"name\\": \\"snowflake-prod\\", \\"type\\": \\"snowflake\\"}, {\\"name\\": \\"github-main\\", \\"type\\": \\"github\\"}]}"}}',
            tool_call_id="call_123",
            name="workspace_shell",
        )

        payload = parse_tool_message_payload(message)
        rows = extract_preview_rows(payload, tool_name=message.name)

        self.assertEqual(
            rows,
            [
                {"name": "snowflake-prod", "type": "snowflake"},
                {"name": "github-main", "type": "github"},
            ],
        )

    def test_validate_marcopolo_email_identity_accepts_email(self) -> None:
        user = UserProfile(
            provider="impersonation",
            providerSubject="developer@example.com",
            subject="impersonation:developer@example.com",
            email="developer@example.com",
            name="Developer",
            issuer="marcopolo-integration-starter",
            emailVerified=True,
        )

        self.assertEqual(validate_marcopolo_email_identity(user), "developer@example.com")

    def test_validate_marcopolo_email_identity_rejects_missing_email(self) -> None:
        user = UserProfile(
            provider="impersonation",
            providerSubject="no-email",
            subject="impersonation:no-email",
            email=None,
            name="Developer",
            issuer="marcopolo-integration-starter",
            emailVerified=True,
        )
        with self.assertRaises(AuthPlatformError) as ctx:
            validate_marcopolo_email_identity(user)

        self.assertIn("email address", ctx.exception.detail)


if __name__ == "__main__":
    unittest.main()
