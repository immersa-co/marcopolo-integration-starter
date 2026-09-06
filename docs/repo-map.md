# Repo Map

This file points developers at the main integration seams in `marcopolo-integration-starter`.

For the higher-level explanation of the connection-management revamp, start with:

- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/docs/connection-setup-sdk-migration.md`

## Frontend

### App shell and tab UI

- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/frontend/src/App.tsx`
- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/frontend/src/app/AppShell.tsx`
- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/frontend/src/auth/`
- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/frontend/src/chatbot/`
- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/frontend/src/connections/`
- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/frontend/src/configuration/`
- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/frontend/src/integrations/`

Contains:

- app bootstrap and tab wiring in `App.tsx`
- shared shell layout in `app/AppShell.tsx`
- auth runtime and login screens in `auth/`
- connections runtime and API/SDK-backed setup and management dialogs in `connections/`
- integrations examples in `integrations/`
- chatbot runtime, trace, and tool inspector in `chatbot/`

## Backend

### Runtime settings

- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/app/core/config.py`
- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/app/core/auth_modes.py`
- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/app/core/dependencies.py`

Contains:

- `.env` settings
- endpoint configuration
- namespace-key and developer-token settings
- `LLM_PROVIDER` switching for the chatbot runtime
- dependency injection and request session resolution

### Authentication session logic

- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/app/services/auth/service.py`
- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/app/services/auth/namespace_tokens.py`
- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/app/services/auth/session_store.py`

Contains:

- demo app-session creation
- selected auth mode persistence
- namespace-key user-token minting
- resolved company and namespace session state

### MarcoPolo integration layer

- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/app/services/platform/marcopolo/service.py`
- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/app/services/platform/marcopolo/session_manager.py`
- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/app/services/platform/marcopolo/skills.py`

Contains:

- MarcoPolo session construction by auth mode
- `list_connections`
- connection type discovery and setup metadata normalization
- dynamic connection creation
- connection lookup and update
- OAuth setup and reauthorization helpers
- connection test and delete
- demo connection install
- `marcopolo-sdk` integration examples
- MCP client interactions

SDK references:

- GitHub: `https://github.com/immersa-co/marcopolo-python-sdk`
- PyPI: `https://pypi.org/project/marcopolo-sdk/`

### Chatbot / LangGraph

- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/app/services/chatbot/service.py`
- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/app/services/chatbot/ai_agent/runtime.py`
- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/app/services/chatbot/ai_agent/mcp_client.py`
- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/app/services/chatbot/ai_agent/tool_registry.py`
- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/app/services/chatbot/ai_agent/context_loader.py`
- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/app/services/chatbot/ai_agent/response_parser.py`
- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/app/api/chatbot.py`

Contains:

- in-memory chat run storage
- direct MCP transport to MarcoPolo
- raw MCP tool binding for LangGraph
- preloaded MarcoPolo skill bootstrap context
- provider-switched LLM construction for OpenAI or Anthropic
- MCP-only `create_react_agent(...)` execution
- `workspace_shell` result normalization
- streaming status and final results

### HTTP API routes

- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/app/api/auth.py`
- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/app/api/connections.py`
- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/app/api/integrations.py`
- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/app/api/configuration.py`
- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/app/api/chatbot.py`

## Tests

- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/tests/test_api_smoke.py`
- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/tests/test_ai_agent_runtime.py`
- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/tests/test_auth_session_contract.py`

Covers:

- basic API shape
- auth protections
- namespace-key auth flow behavior
- connection selection helpers
- integration example selection helpers
- MCP-only runtime streaming and response parsing
- the documented smoke flow in `docs/how-to-sanity-test.md`
