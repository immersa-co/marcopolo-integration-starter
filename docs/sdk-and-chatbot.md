# SDK and Chatbot Guide

The demo intentionally shows two different MarcoPolo consumption patterns.

## 1. SDK Path: Traditional Product Integration

The `Integrations` tab demonstrates the non-agent path using the latest `marcopolo-sdk` package from PyPI.

References:

- GitHub: `https://github.com/immersa-co/marcopolo-python-sdk`
- PyPI: `https://pypi.org/project/marcopolo-sdk/`

Use this when:

- a product feature needs deterministic data access
- an AI agent runtime is unnecessary
- the application wants to render tables, KPIs, or workflow results directly

Current implementation entrypoint:

- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/app/services/platform/marcopolo/service.py`

Flow:

1. resolve the active MarcoPolo auth mode
2. construct a MarcoPolo session
3. call `list_connections`
4. choose the first matching connection for the example
5. call the appropriate `marcopolo-sdk` operation
6. return preview rows to the frontend

Why this matters:

- it shows how a normal application backend can call MarcoPolo without adopting MCP directly in every feature

## 2. Chatbot Path: MCP-Only LangGraph Agent

The `Chatbot` tab demonstrates an MCP-only agent flow. It does not call `marcopolo-sdk` for the agent loop.

Current implementation entrypoints:

- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/app/services/chatbot/service.py`
- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/app/services/chatbot/ai_agent/runtime.py`
- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/app/services/chatbot/ai_agent/mcp_client.py`
- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/app/services/chatbot/ai_agent/tool_registry.py`
- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/app/services/chatbot/ai_agent/context_loader.py`
- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/app/services/chatbot/ai_agent/response_parser.py`
- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/app/api/chatbot.py`

Flow:

1. accept a natural-language prompt
2. resolve the current MarcoPolo bearer token through the shared session manager
3. open a direct Streamable HTTP MCP session against MarcoPolo
4. list the raw MarcoPolo MCP tools and bind them into LangChain `StructuredTool` wrappers
5. preload the three core MarcoPolo skills into the system prompt:
   - `query-and-analyze`
   - `using-connection-cli`
   - `using-marcopolo-workspace`
6. construct the LLM according to `LLM_PROVIDER`
7. run a LangGraph `create_react_agent(...)` loop so the model can choose tools dynamically
8. let the model use `workspace_shell` and the other raw MCP tools directly
9. normalize `workspace_shell` payloads so nested `stdout` JSON becomes preview rows in the UI
10. stream tool-selection and tool-return status events to the frontend, then render final text and any preview table

Why this matters:

- it mirrors the intended MarcoPolo tool surface instead of hiding it behind an SDK adapter
- it keeps the chatbot behavior closer to how Claude or ChatGPT reason over MCP tools and skills
- it demonstrates that LangGraph can orchestrate a reasoning model over raw MarcoPolo tools without hardcoding a bespoke query planner

## LLM Provider Switching

The chatbot runtime now supports:

- `LLM_PROVIDER=openai`
- `LLM_PROVIDER=anthropic`

Shared companion settings:

- `LLM_MODEL`
- `LLM_API_BASE_URL`
- `LLM_API_KEY`

Implementation note:

- `runtime.py` builds `ChatOpenAI` for `openai`
- `runtime.py` builds `ChatAnthropic` for `anthropic`

This keeps the MarcoPolo MCP flow constant while letting you swap the reasoning model provider.

## Connection Management Path

The `Connections` tab demonstrates the supported SDK/API-backed management flow.

Capabilities shown in the demo:

- create connection
- edit connection
- reauthorize OAuth connection
- test connection
- delete connection

The connection-management UI is now driven by backend-normalized SDK metadata rather than the deprecated embedded MCP app path.

## How to Extend the Integrations Tab

To add new examples:

1. add a new `DataConnectionOperationSpec` in `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/app/services/platform/marcopolo/service.py`
2. provide:
   - title
   - prompt
   - target connector type
   - runtime matching terms
   - query payload
3. reload the backend
4. verify the new example appears in `Integrations`

Important design choice:

- the demo resolves the first matching connection at runtime instead of hardcoding one connection slug

That makes the examples more stable across different workspaces.

## How to Evaluate the MCP-Only Chatbot Path

Backend tests:

- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/tests/test_api_smoke.py`
- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/tests/test_ai_agent_runtime.py`

Prompt corpus for regression checks:

- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/tests/fixtures/ai_agent_eval_cases.json`

Run:

```bash
.venv/bin/python -m unittest backend.tests.test_api_smoke backend.tests.test_ai_agent_runtime backend.tests.test_auth_session_contract
```

Manual smoke test:

- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/docs/how-to-sanity-test.md`
