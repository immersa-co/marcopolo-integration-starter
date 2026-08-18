# MarcoPolo Integration Demo

This repository is intended to be published as `marcopolo-integration-starter`.

It is a local reference app with separate frontend and backend processes that shows how a custom web application can integrate MarcoPolo in three ways:

- embedded connection setup through MarcoPolo MCP apps
- traditional product integrations through `marcopolo-sdk`
- agentic workflows through raw MarcoPolo MCP tools and LangGraph
- WorkOS Standalone Connect authorization for a user already authenticated by the partner application

The running app is intentionally presented as **MarcoPolo Integration Demo**. The repository name is **marcopolo-integration-starter** because it is meant to be copied, studied, and extended by developers.

## Start Here

Read the developer guide:

- `docs/README.md`
- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/docs/README.md`

Recommended first path:

1. Copy `.env.example` to `.env` and fill the empty local secret values
2. Start the local Marcopolo stack on `http://localhost:8000`
3. Start the starter backend and frontend
4. Select `WorkOS Standalone Connect (recommended)` and create a demo app session for the partner user
5. Complete the Entelligence WorkOS Standalone Connect flow
6. Confirm the resolved `namespace` and `company` in the session strip
7. Install the Salesforce demo connection and validate the `Integrations` and `Chatbot` tabs

The demo app session represents a user the partner application has already authenticated. WorkOS Standalone Connect
then authorizes MarcoPolo access and resolves the partner namespace; the developer-token mode is only a local shortcut for an already provisioned
workspace and must not be used to validate partner routing.

For the exact browser-based regression flow the repo now uses, see:

- `docs/how-to-sanity-test.md`
- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/docs/how-to-sanity-test.md`

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

## Docs

- Developer Guide: `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/docs/README.md`
- Authentication Modes: `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/docs/authentication-modes.md`
- WorkOS Standalone Connect Flow: `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/docs/workos-connect-authz.md`
- Partner Namespace Manual E2E: `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/docs/partner-namespace-manual-e2e.md`
- Embedded Connection Setup: `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/docs/embedded-connection-setup.md`
- SDK and Chatbot Guide: `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/docs/sdk-and-chatbot.md`
- Sanity Test: `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/docs/how-to-sanity-test.md`
- Repo Map: `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/docs/repo-map.md`
- Known Limitations: `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/docs/known-limitations.md`

## Architecture Split

- `Integrations` is the deterministic product-style path. It uses `marcopolo-sdk` through `backend/app/services/platform/marcopolo/service.py`.
- `Chatbot` is the MCP-only agent path. It uses `backend/app/services/chatbot/ai_agent/` to open a direct MCP session, load raw MarcoPolo tools, preload the three core MarcoPolo skills, and run a LangGraph `create_react_agent(...)` loop without calling the SDK.
- Both paths share the same auth/session resolution. Use WorkOS Standalone Connect to validate the partner flow; the Developer API Token is only an isolated local shortcut.
- `Connections` is the embedded MCP-app path. It uses the backend proxy plus `EmbeddedConnectionSetupHost.tsx` to launch and resume connection setup flows inside the demo UI.
- WorkOS Standalone Connect is not the app's primary login system. The demo first creates a local app session for an already-authenticated user, then obtains a WorkOS access token that the backend forwards to MarcoPolo.

## Current Structure

The repo was recently reorganized so the main code is grouped by feature and shared platform layers.

Backend:

- `backend/app/api/`
  - HTTP route modules: `auth.py`, `chatbot.py`, `configuration.py`, `connections.py`, `integrations.py`
- `backend/app/core/`
  - app settings, auth-mode definitions, and dependency wiring
- `backend/app/models/`
  - API request/response models
- `backend/app/services/auth/`
  - local demo session handling and WorkOS Standalone Connect orchestration
- `backend/app/services/chatbot/`
  - chat run storage and the LangGraph MCP-only agent
- `backend/app/services/platform/marcopolo/`
  - shared MarcoPolo SDK/session/skill substrate used across features

Frontend:

- `frontend/src/auth/`
  - auth gate, runtime bootstrap, and WorkOS redirect logic
- `frontend/src/connections/`
  - connection list, demo install, and embedded setup launcher
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
