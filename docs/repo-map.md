# Repo Map

This file points developers at the main integration seams in `marcopolo-integration-starter`.

For the higher-level explanation of why embedded connection setup exists and how the MCP app host works, start with:

- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/docs/embedded-connection-setup.md`

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
- connections runtime and embedded setup launcher in `connections/`
- integrations examples in `integrations/`
- chatbot runtime, trace, and tool inspector in `chatbot/`

### Embedded MCP app host

- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/frontend/src/EmbeddedConnectionSetupHost.tsx`

Contains:

- iframe host for the MarcoPolo `connection_setup` MCP app
- popup handling for OAuth-style connection setup flows
- setup-session polling and embedded continuation behavior

## Backend

### Runtime settings

- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/app/core/config.py`
- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/app/core/auth_modes.py`
- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/app/core/dependencies.py`

Contains:

- `.env` settings
- endpoint configuration
- Developer API token settings
- WorkOS Connect settings
- dependency injection and request session resolution

### Authentication session logic

- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/app/services/auth/service.py`
- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/app/services/auth/session_store.py`

Contains:

- Test User session creation
- selected auth mode persistence
- WorkOS Connect redirect and callback handling
- Connect refresh handling

### MarcoPolo integration layer

- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/app/services/platform/marcopolo/service.py`
- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/app/services/platform/marcopolo/session_manager.py`
- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/app/services/platform/marcopolo/skills.py`

Contains:

- MarcoPolo session construction by auth mode
- `list_connections`
- demo connection install
- embedded connection setup
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
- MCP-only `create_react_agent(...)` execution
- `workspace_shell` result normalization
- streaming status + final results

### HTTP API routes

- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/app/api/auth.py`
- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/app/api/connections.py`
- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/app/api/integrations.py`
- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/app/api/configuration.py`
- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/app/api/chatbot.py`

## Tests

- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/tests/test_api_smoke.py`

Covers:

- basic API shape
- auth protections
- connection selection helpers
- integration example selection helpers
- MCP-only runtime streaming and response parsing
- current smoke flow is documented separately in `docs/how-to-sanity-test.md`
