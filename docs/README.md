# Developer Guide

This guide is the recommended onboarding path for `marcopolo-integration-starter`.

## What This Demo Shows

- how to authorize MarcoPolo access with WorkOS Standalone Connect after the partner app authenticates its user
- how the session exposes Marcopolo's issuer-resolved namespace and company
- how to list and configure MarcoPolo connections from a custom web app
- how to use `marcopolo-sdk` for traditional product integrations
- how to use raw MarcoPolo MCP tools from an MCP-only LangGraph agent
- how the embedded MCP app connection configuration approach works

## Recommended Learning Path

### 1. Getting Started: Partner Namespace E2E

1. Start the local Marcopolo stack on `http://localhost:8000`.
2. Copy `.env.example` to `.env`.
3. Fill the empty secret values. The example already contains the local Marcopolo URLs, canonical
   `/api/auth/bootstrap`, and the Entelligence AuthKit domain and client ID.
4. Install dependencies:

   ```bash
   python3 -m venv .venv
   .venv/bin/python -m pip install -r backend/requirements.txt
   npm --prefix frontend install
   ```

5. Run the backend and frontend:

   ```bash
   .venv/bin/python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8001
   npm --prefix frontend run dev -- --host 0.0.0.0 --port 5173
   ```

6. Open `http://localhost:5173` and choose `WorkOS Standalone Connect (recommended)`.
7. Create a demo app session for the partner user, then complete WorkOS Standalone Connect.
8. Confirm the session strip shows the authoritative values:

   - `namespace: entelligence`
   - `company: entelligence-demo`

The demo app session represents a user the partner application has already authenticated. The backend exchanges the
WorkOS code, calls Marcopolo `POST /api/auth/bootstrap` with the access and refresh tokens, validates the response,
and stores the returned namespace and company. A failed bootstrap leaves the session unprovisioned.

### 2. List Available Connections

After the WorkOS Standalone Connect bootstrap succeeds, open the `Connections` tab and click `Refresh`. The backend uses the
WorkOS access token associated with the bootstrapped session and the UI renders the visible namespace connections.

### 3. Create the Salesforce Demo Connection

In `Connections`:

1. In `Install Demo Connection`, enter `salesforce`
2. Click `Install Demo Connection`
3. Click `Refresh`
4. Confirm Salesforce appears in the available connection list

This is the fastest way to get a known-good connection for testing both SDK and agent flows.

### 4. Understand `marcopolo-sdk`

The backend uses the published `marcopolo-sdk` package for product-style integrations.

References:

- GitHub: `https://github.com/immersa-co/marcopolo-python-sdk`
- PyPI: `https://pypi.org/project/marcopolo-sdk/`

Relevant implementation:

- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/app/services/platform/marcopolo/service.py`

The important flow is:

1. build a MarcoPolo bearer token for the selected auth mode
2. construct the SDK client
3. select an available connection at runtime
4. call `client.execute(...)`
5. render the returned rows in the app UI

This is the pattern to follow for non-agent features in a product.

### 5. Use the Integrations Section to Test Salesforce

In `Integrations`:

1. Click the Salesforce prompt
2. Confirm rows render in the result table

This demonstrates a product feature invoking MarcoPolo through `marcopolo-sdk` without involving the Chatbot or LangGraph.

### 6. Use the Chatbot to Test Salesforce

In `Chatbot`:

1. Ask a Salesforce question such as `List top 5 customer accounts by revenue from Salesforce.`
2. Confirm the progress stream advances through tool-selection and tool-return status events
3. Confirm preview rows render in the table output

This demonstrates the agent path:

- the backend opens a direct MCP session to MarcoPolo
- LangGraph runs a tool-calling loop over the raw MarcoPolo MCP tools
- the model can use `workspace_shell` and other exposed MCP tools directly
- the backend normalizes nested `workspace_shell` results into preview rows
- the final response and preview rows are rendered in the chat UI

### 7. Configure and Test Other Connections

After Salesforce is working:

1. Use `Connections -> Connect a Data Source`
2. Enter a supported connection type such as `jira`
3. Complete the embedded setup flow
4. Click `Refresh`
5. Extend the integration examples or ask the Chatbot about the new connection

To add more SDK-driven examples, edit the SDK example definitions in:

- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/app/services/platform/marcopolo/service.py`

For a deeper explanation of how the embedded connection configuration host works, read:

- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/docs/embedded-connection-setup.md`

### 8. Local Developer Token Shortcut

The `Developer API Token (local shortcut)` mode is available only for inspecting an already provisioned workspace.
It is not the partner integration and provides no proof of WorkOS issuer-based namespace resolution. Do not use it for
the Entelligence E2E.

## Next Reading

- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/docs/partner-namespace-manual-e2e.md`
- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/docs/authentication-modes.md`
- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/docs/embedded-connection-setup.md`
- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/docs/sdk-and-chatbot.md`
- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/docs/repo-map.md`
- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/docs/known-limitations.md`
- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/docs/how-to-sanity-test.md`
