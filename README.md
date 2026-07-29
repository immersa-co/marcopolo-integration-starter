# MarcoPolo Integration Demo

This repository is intended to be published as `marcopolo-integration-starter`.

It is a local reference app with separate frontend and backend processes that shows how a custom web application can integrate MarcoPolo in three ways:

- embedded connection setup through MarcoPolo MCP apps
- traditional product integrations through `marcopolo-sdk`
- agentic workflows through MarcoPolo MCP tools and LangGraph

The running app is intentionally presented as **MarcoPolo Integration Demo**. The repository name is **marcopolo-integration-starter** because it is meant to be copied, studied, and extended by developers.

## Start Here

Read the developer guide:

- `docs/README.md`
- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/docs/README.md`

Recommended first path:

1. Copy `.env.example` to `.env` and fill the empty local secret values
2. Start the local Marcopolo stack on `http://localhost:8000`
3. Start the starter backend and frontend
4. Select `WorkOS Connect (partner E2E)` and enter the partner user's email as the Test User
5. Complete the Entelligence WorkOS Connect flow
6. Confirm the resolved `namespace` and `company` in the session strip
7. Install the Salesforce demo connection and validate the `Integrations` and `Chatbot` tabs

The Test User is a demo harness for the partner application's authenticated user. WorkOS Connect is the only
partner namespace authentication path; the developer-token mode is only a local shortcut for an already provisioned
workspace and must not be used to validate partner routing.

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
- Partner Namespace Manual E2E: `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/docs/partner-namespace-manual-e2e.md`
- Embedded Connection Setup: `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/docs/embedded-connection-setup.md`
- SDK and Chatbot Guide: `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/docs/sdk-and-chatbot.md`
- Repo Map: `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/docs/repo-map.md`
- Known Limitations: `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/docs/known-limitations.md`

## Repo Scope

This is a demo, not a production starter kit. It intentionally keeps:

- an in-memory session model
- a Test User email entry flow
- a thin backend around MarcoPolo
- a separate frontend and backend local runtime

It is designed to help application developers understand the integration seams, not to prescribe the final production architecture.
