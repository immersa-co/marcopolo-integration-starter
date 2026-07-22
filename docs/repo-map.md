# Repo Map

This file points developers at the main integration seams in `marcopolo-integration-starter`.

## Frontend

### App shell and tab UI

- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/frontend/src/App.tsx`

Contains:

- Test User entry flow
- auth mode selector
- connections list and refresh
- install demo connection form
- embedded connection setup launcher
- integrations result rendering
- chatbot result rendering

### Embedded MCP app host

- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/frontend/src/RealEmbeddedConnectionSetupHost.tsx`

Contains:

- iframe host for the MarcoPolo `connection_setup` MCP app
- popup handling for OAuth-style connection setup flows
- setup-session polling and embedded continuation behavior

## Backend

### Runtime settings

- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/app/config.py`

Contains:

- `.env` settings
- endpoint configuration
- Developer API token settings
- WorkOS Connect settings

### Authentication session logic

- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/app/services/auth.py`
- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/app/services/auth_session_store.py`

Contains:

- Test User session creation
- selected auth mode persistence
- WorkOS Connect redirect and callback handling
- Connect refresh handling

### MarcoPolo integration layer

- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/app/services/marcopolo.py`

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

- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/app/services/langgraph_agent.py`
- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/app/api/chat.py`

Contains:

- prompt planning
- connection selection
- MCP-backed execution
- streaming status + final results

### HTTP API routes

- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/app/api/auth.py`
- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/app/api/connections.py`
- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/app/api/integrations.py`
- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/app/api/config.py`

## Tests

- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/tests/test_api_smoke.py`

Covers:

- basic API shape
- auth protections
- connection selection helpers
- integration example selection helpers
