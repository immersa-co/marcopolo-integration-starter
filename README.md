# MarcoPolo Integration Demo

This is a reference app with separate frontend and backend processes. It shows how a partner application can integrate with **MarcoPolo production**, using the MarcoPolo python API SDK as well as MCP Protocol.

The following use patterns are demonstrated:

- Authorize calls to MarcoPolo using namespace-key token to create and work with named user workspaces
- Install demo datasource connections in the workspace
- Manage (create, update, test, delete) data source connections for the workspace
- Implement LangGraph agentic workflows using MarcoPolo MCP tools 

The running app is intentionally presented as **MarcoPolo Integration Demo**. The repository name is **marcopolo-integration-starter** because it is meant to be copied, studied, and extended by developers.

## Start Here

Read the developer guide first:

- `docs/README.md`

Recommended first path:

1. Copy `.env.example` to `.env`.
2. Fill the required production MarcoPolo and LLM settings.
3. Ask the MarcoPolo team for a valid `MARCOPOLO_NAMESPACE_KEY`.
4. Start the backend and frontend.
5. Open `http://localhost:5173`.
6. Choose `Namespace key (recommended)`.
7. Create a demo app session for a named production user account (email)
8. Confirm the resolved `namespace` and `company` in the session strip.
9. Install the Salesforce demo connection or use `Add Data Source to create any supported connection`.
10. Refresh the list of connections and edit and test the connections.
11. From the `Integrations`tab, click the Salesforce question to get response from Salesforce demo connection
12. From the Chatbot tab, ask any natural language question for any created valid connection, just like you would from Claude Desktop or ChatGPT.

The demo app session represents a user the partner application already authenticated. In the recommended mode, the backend uses a MarcoPolo namespace key to mint a short-lived user token and resolve the correct namespace and company for that user. The developer-token mode is only a local shortcut for your existing MarcoPolo workspace in case its convenient to test this without getting a Namespace key from the MarcoPolo team.

For the browser-based regression flow the repo uses, see:

- `docs/how-to-sanity-test.md` 

## Prerequisites

Required tools:

- `python3` 3.11+
- `pip`
- `node` 20+
- `npm` 10+

Optional check:

```bash
./scripts/check-prereqs.sh
```

## Local Setup

```bash
cp .env.example .env
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
npm --prefix frontend install
```

Run:

```bash
.venv/bin/python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8001
npm --prefix frontend run dev -- --host 0.0.0.0 --port 5173
```

Open `http://localhost:5173`.

## Required Configuration

Minimum production-oriented settings:

- `SESSION_SECRET`
- `MARCOPOLO_MCP_URL`
- `MARCOPOLO_API_BASE_URL`
- `MARCOPOLO_WEB_BASE_URL`
- `MARCOPOLO_NAMESPACE_KEY`
- `LLM_PROVIDER`
- `LLM_MODEL`
- `LLM_API_BASE_URL`
- `LLM_API_KEY`
- `SKILL_REPO_PATH`

Notes:

- Get `MARCOPOLO_NAMESPACE_KEY` from the MarcoPolo team.
- Use a valid MarcoPolo production user email in the demo app session form.
- `LLM_PROVIDER` currently supports `openai` and `anthropic`.

## Docs

- Developer Guide: `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/docs/README.md`
- Authentication Modes: `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/docs/authentication-modes.md`
- Partner Namespace Manual E2E: `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/docs/partner-namespace-manual-e2e.md`
- Connection Setup Migration Note: `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/docs/connection-setup-sdk-migration.md`
- SDK and Chatbot Guide: `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/docs/sdk-and-chatbot.md`
- Sanity Test: `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/docs/how-to-sanity-test.md`
- Repo Map: `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/docs/repo-map.md`
- Known Limitations: `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/docs/known-limitations.md`



## Architecture Split

- `Connections` is the SDK/API-backed connection-management path. It supports:
  - create connection
  - edit connection
  - reauthorize OAuth connections
  - test connection
  - delete connection
- `Integrations` is the deterministic product-style path. It uses `marcopolo-sdk` through `backend/app/services/platform/marcopolo/service.py`.
- `Chatbot` is the MCP-only agent path. It uses `backend/app/services/chatbot/ai_agent/` to open a direct MCP session, load raw MarcoPolo tools, preload the core MarcoPolo skills, and run a LangGraph `create_react_agent(...)` loop without calling the SDK.
- Namespace-key auth is not the app's primary login system. The demo first creates a local app session for an already-authenticated user, then exchanges the configured MarcoPolo namespace key for a short-lived user token.

## Current Structure

Backend:

- `backend/app/api/`
  - HTTP route modules: `auth.py`, `chatbot.py`, `configuration.py`, `connections.py`, `integrations.py`
- `backend/app/core/`
  - app settings, auth-mode definitions, and dependency wiring
- `backend/app/models/`
  - API request/response models
- `backend/app/services/auth/`
  - local demo session handling and namespace-key auth orchestration
- `backend/app/services/chatbot/`
  - chat run storage and the LangGraph MCP-only agent
- `backend/app/services/platform/marcopolo/`
  - shared MarcoPolo SDK, session, MCP, and skill substrate used across features

Frontend:

- `frontend/src/auth/`
  - auth gate and runtime bootstrap
- `frontend/src/connections/`
  - connection list, demo install, add/edit/test/delete dialogs, and API/SDK-backed setup flows
- `frontend/src/integrations/`
  - deterministic SDK-backed examples
- `frontend/src/chatbot/`
  - LangGraph trace UI, tool inspector, and chat runtime
- `frontend/src/configuration/`
  - runtime configuration panel
- `frontend/src/app/`
  - shared shell and app-level types/constants

## Repo Scope

This is a demo, not a production starter kit. It intentionally keeps:

- an in-memory session model
- a demo app-session email flow
- a thin backend around MarcoPolo
- a separate frontend and backend local runtime

It is designed to help application developers understand the integration seams, not to prescribe the final production architecture.