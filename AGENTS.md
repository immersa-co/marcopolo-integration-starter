# AGENTS.md

## Purpose

This repository is a demo for four related integration paths:

- MarcoPolo namespace-key token minting for the selected demo user
- API and SDK-backed connection setup through a dynamic dialog
- deterministic SDK-backed product integrations
- an MCP-only LangGraph agent that uses raw MarcoPolo tools

Keep `README.md` human-oriented and use this file as the canonical onboarding guide for coding agents.

## Prerequisites Check

Before setup, verify these commands exist:

```bash
git --version
python3 --version
pip --version
node --version
npm --version
```

Or run:

```bash
./scripts/check-prereqs.sh
```

If any command is missing:

- stop
- tell the user exactly which dependency is missing
- ask them to install it before continuing

Recommended versions:

- `python3` 3.11+
- `node` 20+
- `npm` 10+

## First Questions To Ask The User

Ask these before trying to run the app if the answers are not already clear:

1. Which MarcoPolo auth mode should be used?
   - `namespace_key`
   - `developer_api_token`
2. If `namespace_key`:
   - confirm `MARCOPOLO_NAMESPACE_KEY` is configured
   - ask for the valid MarcoPolo user email to impersonate in the demo app session
3. If `developer_api_token`:
   - ask for `MARCOPOLO_DEVELOPER_API_TOKEN`
   - ask for the MarcoPolo email that owns that workspace
4. Confirm whether `LLM_API_KEY` is already configured

## Environment Setup

Copy the example env file and fill in the required secrets:

```bash
cp .env.example .env
```

The simplest path uses:

- `SESSION_SECRET`
- `MARCOPOLO_MCP_URL`
- `MARCOPOLO_API_BASE_URL`
- `MARCOPOLO_WEB_BASE_URL`
- `MARCOPOLO_NAMESPACE_KEY`
- `MARCOPOLO_DEVELOPER_API_TOKEN`
- `LLM_API_KEY`
- `SKILL_REPO_PATH`

## Install

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
npm --prefix frontend install
```

## Run

Backend:

```bash
.venv/bin/python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8001
```

Frontend:

```bash
npm --prefix frontend run dev -- --host 0.0.0.0 --port 5173
```

Open:

- `http://localhost:5173`

## Verification

Use the canonical smoke test:

- `docs/how-to-sanity-test.md`

Preferred validation flow:

1. Open `http://localhost:5173`
2. Choose `Namespace key (recommended)` when available
3. Enter a valid user email such as `<user>@<domain>`
4. Click `Create demo app session`
5. Open `Chatbot`
6. Ask `List top 5 customers by revenue from Salesforce`
7. Wait for the LangGraph agent to return the ranked result

If that passes, the current MCP-only chatbot path is working end to end.

Notes:

- For `namespace_key`, the test email should be valid for the configured MarcoPolo environment.
- For `developer_api_token`, prefer the email that owns the MarcoPolo workspace behind `MARCOPOLO_DEVELOPER_API_TOKEN`.

## Repo Map

Backend:

- `backend/app/api/`
  - route modules: `auth.py`, `chatbot.py`, `configuration.py`, `connections.py`, `integrations.py`
- `backend/app/core/`
  - settings, auth-mode definitions, dependency wiring
- `backend/app/models/`
  - API request/response models
- `backend/app/services/auth/`
  - local demo session handling and namespace-key auth orchestration
- `backend/app/services/chatbot/`
  - chat storage and LangGraph MCP-only agent runtime
- `backend/app/services/platform/marcopolo/`
  - shared MarcoPolo SDK/session/skill substrate

Frontend:

- `frontend/src/auth/`
- `frontend/src/connections/`
- `frontend/src/integrations/`
- `frontend/src/chatbot/`
- `frontend/src/configuration/`
- `frontend/src/app/`

## Important Constraints

- The `Chatbot` path must use raw MarcoPolo MCP tools, not the SDK
- `Integrations` is the deterministic SDK-backed path
- `Connections` is the API/SDK-backed connection setup path

## Useful Docs

- `README.md`
- `docs/README.md`
- `docs/sdk-and-chatbot.md`
- `docs/repo-map.md`
- `docs/how-to-sanity-test.md`
