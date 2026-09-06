import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from langchain_core.messages import ToolMessage

from backend.app.services.chatbot.ai_agent.connection_matching import match_visible_connection
from backend.app.services.chatbot.ai_agent.response_parser import (
    extract_preview_rows,
    extract_tool_error,
    normalize_tool_payload,
    parse_tool_message_payload,
)
from backend.app.services.platform.marcopolo.service import (
    _DATA_CONNECTION_OPERATION_SPEC_INDEX,
    _select_operation_connection,
)
from backend.app.services.auth import AuthPlatformError, validate_marcopolo_email_identity
from backend.app.main import app
from backend.app.models.api import ConnectionListItem, UserProfile
from backend.app.services.platform import MarcoPoloService


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
        self.assertIsNone(session_payload["company"])
        self.assertIsNone(session_payload["namespace"])

        examples_response = self.client.get("/api/integrations/examples")
        self.assertEqual(examples_response.status_code, 200)
        self.assertEqual(len(examples_response.json()["examples"]), 3)

    def test_demo_session_route_creates_demo_session(self) -> None:
        response = self.client.post("/api/auth/demo-session", json={"email": "demo.user@example.com"})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["authenticated"])
        self.assertEqual(payload["provider"], "demo_session")
        self.assertEqual(payload["user"]["email"], "demo.user@example.com")
        self.assertEqual(payload["user"]["subject"], "demo_session:demo.user@example.com")
        self.assertFalse(payload["marcoPoloProvisioned"])
        self.assertIsNone(payload["company"])
        self.assertIsNone(payload["namespace"])

        session_payload = self.client.get("/api/auth/session").json()
        self.assertTrue(session_payload["authenticated"])
        self.assertEqual(session_payload["provider"], "demo_session")
        self.assertEqual(session_payload["user"]["email"], "demo.user@example.com")
        self.assertIsNone(session_payload["company"])
        self.assertIsNone(session_payload["namespace"])

        logout_response = self.client.post("/api/auth/logout")
        self.assertEqual(logout_response.status_code, 200)
        logout_payload = logout_response.json()
        self.assertFalse(logout_payload["marcoPoloProvisioned"])
        self.assertIsNone(logout_payload["company"])
        self.assertIsNone(logout_payload["namespace"])

    def test_legacy_impersonate_route_is_not_exposed(self) -> None:
        response = self.client.post("/api/auth/impersonate", json={"email": "demo.user@example.com"})
        self.assertEqual(response.status_code, 404)

    def test_protected_routes_require_authentication(self) -> None:
        connections = self.client.get("/api/connections")
        self.assertEqual(connections.status_code, 401)

        connection_types = self.client.get("/api/connections/types")
        self.assertEqual(connection_types.status_code, 401)

        connection_type_detail = self.client.get("/api/connections/types/snowflake")
        self.assertEqual(connection_type_detail.status_code, 401)

        create_connection = self.client.post(
            "/api/connections",
            json={
                "connectionType": "snowflake",
                "displayName": "Finance Snowflake",
                "setupMethod": "credentials",
                "fields": {},
            },
        )
        self.assertEqual(create_connection.status_code, 401)

        get_connection = self.client.get("/api/connections/snowflake-finance")
        self.assertEqual(get_connection.status_code, 401)

        update_connection = self.client.patch(
            "/api/connections/snowflake-finance",
            json={"displayName": "Finance Snowflake"},
        )
        self.assertEqual(update_connection.status_code, 401)

        delete_connection = self.client.delete("/api/connections/snowflake-finance")
        self.assertEqual(delete_connection.status_code, 401)

        chat = self.client.post("/api/chat", json={"message": "hello"})
        self.assertEqual(chat.status_code, 401)

        integration_run = self.client.post("/api/integrations/run", json={"exampleId": "jira_open_tickets"})
        self.assertEqual(integration_run.status_code, 401)

        marcopolo_authorize = self.client.get("/api/auth/marcopolo/authorize", follow_redirects=False)
        self.assertEqual(marcopolo_authorize.status_code, 401)

        reauthorize = self.client.post(
            "/api/connections/snowflake-finance/reauthorize",
            json={"clientSessionId": "demo"},
        )
        self.assertEqual(reauthorize.status_code, 401)

    def test_connection_type_list_route_returns_normalized_contract(self) -> None:
        with self.client as client:
            auth_response = client.post("/api/auth/demo-session", json={"email": "demo.user@example.com"})
            self.assertEqual(auth_response.status_code, 200)

            fake_response = {
                "connectionTypes": [
                    {
                        "type": "snowflake",
                        "displayName": "Snowflake",
                        "category": "warehouse",
                        "description": "Cloud warehouse",
                        "authMethods": ["manual"],
                        "setupMethodKinds": ["fields"],
                        "requiresOAuth": False,
                        "deprecated": False,
                    }
                ]
            }

            with patch.object(
                MarcoPoloService,
                "list_connection_types",
                new=AsyncMock(return_value=fake_response),
            ) as mocked:
                response = client.get(
                    "/api/connections/types",
                    params={"search": "snow", "authMethod": "manual"},
                )

            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(payload["connectionTypes"][0]["type"], "snowflake")
            self.assertEqual(payload["connectionTypes"][0]["setupMethodKinds"], ["fields"])
            mocked.assert_awaited_once()

    def test_connection_type_detail_route_returns_setup_methods(self) -> None:
        with self.client as client:
            auth_response = client.post("/api/auth/demo-session", json={"email": "demo.user@example.com"})
            self.assertEqual(auth_response.status_code, 200)

            fake_response = {
                "type": "snowflake",
                "displayName": "Snowflake",
                "category": "warehouse",
                "description": "Cloud warehouse",
                "authMethods": ["manual"],
                "uiFeatures": {
                    "deleteWarning": "default",
                    "filePicker": [],
                    "isFileProvider": False,
                    "isPersonal": False,
                    "logoKey": None,
                    "requiresOAuth": False,
                    "supportsDownload": False,
                    "supportsUpload": False,
                    "usesLocalFilePicker": False,
                },
                "setupMethods": [
                    {
                        "method": "credentials",
                        "kind": "fields",
                        "category": "manual",
                        "displayName": "Credentials",
                        "description": "Provide credentials.",
                        "fields": [
                            {
                                "name": "account",
                                "type": "string",
                                "required": True,
                                "secret": False,
                                "label": "Account",
                                "description": "Snowflake account.",
                                "advanced": False,
                                "choices": None,
                                "default": None,
                                "file": None,
                                "groupLabel": "Basics",
                                "itemType": None,
                                "minItems": None,
                            }
                        ],
                    }
                ],
            }

            with patch.object(
                MarcoPoloService,
                "get_connection_type",
                new=AsyncMock(return_value=fake_response),
            ) as mocked:
                response = client.get("/api/connections/types/snowflake")

            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(payload["setupMethods"][0]["method"], "credentials")
            self.assertEqual(payload["setupMethods"][0]["fields"][0]["name"], "account")
            mocked.assert_awaited_once()

    def test_create_connection_route_returns_created_connection(self) -> None:
        with self.client as client:
            auth_response = client.post("/api/auth/demo-session", json={"email": "demo.user@example.com"})
            self.assertEqual(auth_response.status_code, 200)

            fake_response = {
                "connection": {
                    "name": "snowflake-finance-snowflake",
                    "type": "snowflake",
                    "displayName": "Finance Snowflake",
                    "category": "warehouse",
                    "authMethod": "manual",
                    "canManage": True,
                },
                "message": "Connection created successfully.",
            }

            with patch.object(
                MarcoPoloService,
                "create_connection",
                new=AsyncMock(return_value=fake_response),
            ) as mocked:
                response = client.post(
                    "/api/connections",
                    json={
                        "connectionType": "snowflake",
                        "displayName": "Finance Snowflake",
                        "setupMethod": "credentials",
                        "fields": {"account": "acme-west"},
                    },
                )

            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(payload["connection"]["name"], "snowflake-finance-snowflake")
            self.assertEqual(payload["connection"]["authMethod"], "manual")
            mocked.assert_awaited_once()

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
                authMethod="manual",
                canManage=True,
                accessReason="owner",
                capabilities=["query"],
            ),
            ConnectionListItem(
                name="other-connection",
                displayName="Other",
                type="postgres",
                authMethod="manual",
                canManage=True,
                accessReason="owner",
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
            provider="demo_session",
            providerSubject="developer@example.com",
            subject="demo_session:developer@example.com",
            email="developer@example.com",
            name="Developer",
            issuer="marcopolo-integration-starter",
            emailVerified=True,
        )

        self.assertEqual(validate_marcopolo_email_identity(user), "developer@example.com")

    def test_validate_marcopolo_email_identity_rejects_missing_email(self) -> None:
        user = UserProfile(
            provider="demo_session",
            providerSubject="no-email",
            subject="demo_session:no-email",
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
