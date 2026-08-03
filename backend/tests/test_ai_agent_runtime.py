import json
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from langchain_core.messages import AIMessage, ToolMessage

from backend.app.config import get_settings
from backend.app.models import UserProfile
from backend.app.services.ai_agent.context_loader import AgentBootstrapContext
from backend.app.services.ai_agent.runtime import IntegrationDemoAgentService, _system_prompt
from backend.app.services.auth import UserSession
from backend.app.services.chat import ChatRun
from backend.app.services.skills import SkillRegistry


class _FakeStreamingAgent:
    def __init__(self, updates):
        self._updates = updates

    async def astream(self, _inputs, stream_mode):
        if stream_mode != "updates":
            raise AssertionError("stream_chat should request LangGraph updates mode")
        for update in self._updates:
            yield update


class AiAgentRuntimeTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.settings = get_settings()
        self.skills = SkillRegistry([])
        self.service = IntegrationDemoAgentService(self.settings, None, self.skills)
        self.service._model = Mock(return_value=object())  # type: ignore[method-assign]
        self.service._tool_registry.build_langchain_tools = AsyncMock(return_value=[])  # type: ignore[method-assign]

    async def test_stream_chat_surfaces_tool_trace_and_workspace_shell_rows(self) -> None:
        updates = [
            {
                "agent": {
                    "messages": [
                        AIMessage(
                            content="",
                            usage_metadata={
                                "input_tokens": 1200,
                                "output_tokens": 180,
                                "total_tokens": 1380,
                            },
                            tool_calls=[
                                {
                                    "id": "call_123",
                                    "name": "workspace_shell",
                                    "args": {"command": "connection list --json"},
                                    "type": "tool_call",
                                }
                            ],
                        )
                    ]
                }
            },
            {
                "tools": {
                    "messages": [
                        ToolMessage(
                            tool_call_id="call_123",
                            name="workspace_shell",
                            content=(
                                '{"structuredContent":{"success":true,"exit_code":0,"stdout":"{\\"success\\": true, '
                                '\\"connections\\": [{\\"name\\": \\"snowflake-prod\\", \\"type\\": \\"snowflake\\"}, '
                                '{\\"name\\": \\"github-main\\", \\"type\\": \\"github\\"}]}"}}'
                            ),
                        )
                    ]
                }
            },
            {
                "agent": {
                    "messages": [
                        AIMessage(content="I found two connections that match the request.")
                    ]
                }
            },
        ]

        user = UserProfile(
            provider="test",
            providerSubject="test-user",
            subject="test-user",
            email="test@example.com",
            name="Test User",
            issuer="local",
            emailVerified=True,
        )
        session = UserSession(
            authenticated=True,
            user=user,
            marcopolo_auth_mode="developer_api_token",
        )
        chat_run = ChatRun(chat_id="chat-1", message="List connections", user_session=session)

        with patch(
            "backend.app.services.ai_agent.runtime.create_react_agent",
            return_value=_FakeStreamingAgent(updates),
        ):
            events = [event async for event in self.service.stream_chat(chat_run)]

        statuses = [json.loads(event["data"]) for event in events if event["event"] == "status"]
        final = json.loads(next(event["data"] for event in events if event["event"] == "final"))

        self.assertIn(
            {
                "node": "agent",
                "message": "Model selected tool call(s): workspace_shell",
                "toolName": "workspace_shell",
                "toolCallIds": ["call_123"],
                "toolCalls": [{"id": "call_123", "name": "workspace_shell"}],
                "tokenUsage": {
                    "input": 1200,
                    "output": 180,
                    "total": 1380,
                    "source": "usage_metadata",
                    "approximate": False,
                    "sharedAcrossToolCalls": 1,
                },
            },
            statuses,
        )
        self.assertIn(
            {"node": "tools", "message": "Tool returned: workspace_shell", "toolName": "workspace_shell", "toolCallIds": ["call_123"]},
            statuses,
        )
        self.assertEqual(final["resultKind"], "table")
        self.assertEqual(
            final["table"],
            [
                {"name": "snowflake-prod", "type": "snowflake"},
                {"name": "github-main", "type": "github"},
            ],
        )

        debug_tool_requests = [json.loads(event["data"]) for event in events if event["event"] == "debug_tool"]
        self.assertTrue(
            any(
                event.get("phase") == "request"
                and event.get("toolCallId") == "call_123"
                and event.get("tokenUsage", {}).get("total") == 1380
                for event in debug_tool_requests
            )
        )

    def test_system_prompt_includes_preloaded_skills_and_dynamic_guidance_note(self) -> None:
        prompt = _system_prompt(
            AgentBootstrapContext(
                skill_names=("query-and-analyze", "using-connection-cli"),
                skill_documents=(),
                combined_text="Skill A\n\nSkill B",
            )
        )

        self.assertIn("Use the available MarcoPolo MCP tools", prompt)
        self.assertIn("Connection-specific guidance may be read dynamically", prompt)
        self.assertIn("Preloaded MarcoPolo skills:", prompt)
        self.assertIn("Skill A", prompt)

    def test_eval_fixture_is_well_formed(self) -> None:
        fixture_path = Path(__file__).with_name("fixtures") / "ai_agent_eval_cases.json"
        cases = json.loads(fixture_path.read_text(encoding="utf-8"))

        self.assertGreaterEqual(len(cases), 4)
        self.assertTrue(all(case.get("id") for case in cases))
        self.assertTrue(all(case.get("prompt") for case in cases))
        self.assertTrue(all(case.get("expected_tool") == "workspace_shell" for case in cases))
        self.assertGreaterEqual(len({case.get("connector_type") for case in cases}), 4)


if __name__ == "__main__":
    unittest.main()
