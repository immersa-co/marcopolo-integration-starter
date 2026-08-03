# SDK and Chatbot Guide

The demo intentionally shows two different MarcoPolo consumption patterns.

## 1. SDK Path: Traditional Product Integration

The `Integrations` tab demonstrates the non-agent path using `marcopolo-sdk`.

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
5. call `marcopolo-sdk` `execute(...)`
6. return preview rows to the frontend

Why this matters:

- it shows how a normal application backend can call MarcoPolo without adopting MCP directly in every feature

## 2. Chatbot Path: MCP-Only LangGraph Agent

The `Chatbot` tab demonstrates an MCP-only agent flow. It does not call `marcopolo-sdk`.

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
6. run a LangGraph `create_react_agent(...)` loop so the model can choose tools dynamically
7. let the model use `workspace_shell` and the other raw MCP tools directly
8. normalize `workspace_shell` payloads so nested `stdout` JSON becomes preview rows in the UI
9. stream tool-selection and tool-return status events to the frontend, then render final text and any preview table

Why this matters:

- it mirrors the intended MarcoPolo tool surface instead of hiding it behind an SDK adapter
- it keeps the chatbot behavior closer to how Claude or ChatGPT reason over MCP tools and skills
- it demonstrates that LangGraph can orchestrate a reasoning model over raw MarcoPolo tools without hardcoding a bespoke query planner

Important design choices:

- the chatbot path shares auth resolution with the rest of the app, so it works with either `MARCOPOLO_DEVELOPER_API_TOKEN` or `WorkOS Connect`
- the chatbot path intentionally trusts the model plus the preloaded MarcoPolo skills rather than hardcoding a fixed "always read syntax first" workflow
- connection-specific files are expected to be read dynamically through `workspace_shell` when the model decides they are needed
- the repository now contains a single authoritative chatbot path under `backend/app/services/chatbot/`

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
.venv/bin/python -m unittest backend.tests.test_api_smoke backend.tests.test_ai_agent_runtime
```

Manual smoke test:

- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/docs/how-to-sanity-test.md`

## Recommended First Validation

1. install the Salesforce demo connection
2. run the Salesforce integration example
3. ask the Chatbot a Salesforce or connection-list question
4. add Jira
5. add a Jira integration example or ask the Chatbot about Jira
