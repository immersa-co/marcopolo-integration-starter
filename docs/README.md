# Developer Guide

This guide is the recommended onboarding path for `marcopolo-integration-starter`.

## What This Demo Shows

- how to get started by authenticating to MarcoPolo with your own personal Developer API token 
- how to switch to WorkOS Connect token mode
- how to list and configure MarcoPolo connections from a custom web app
- how to use `marcopolo-sdk` for traditional product integrations
- how to use MarcoPolo MCP tools from a LangGraph agent

## Recommended Learning Path

### 1. Getting Started


1. First, create a [**Developer API token**](https://docs.marcopolo.dev/getting-started/developer-sdk#api-tokens) using your own MarcoPolo login
3. Copy `.env.example` to `.env`
4. Set:
   - `SESSION_SECRET`
   - `MARCOPOLO_MCP_URL`
   - `MARCOPOLO_API_BASE_URL`
   - `MARCOPOLO_WEB_BASE_URL`
   - `MARCOPOLO_DEVELOPER_API_TOKEN`
   - `LLM_API_KEY`
   - `SKILL_REPO_PATH`

Install dependencies:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
npm --prefix frontend install
```

Run the app:

```bash
.venv/bin/python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8001
npm --prefix frontend run dev -- --host 0.0.0.0 --port 5173
```

Open `http://localhost:5173`.

### 2. Login Using Developer API Token and List Available Connections

In the launch page:

1. Leave the auth mode on `Developer API Token`
2. Enter the same email that owns the MarcoPolo workspace behind your Developer API token
3. Click `Test User`
4. Open the `Connections` tab
5. Click `Refresh`

That exercises the simplest dial tone:

- frontend asks backend for connections
- backend builds a MarcoPolo session from `MARCOPOLO_DEVELOPER_API_TOKEN`
- backend calls `list_connections`
- the UI renders the visible workspace connections

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

- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/app/services/marcopolo.py`

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
2. Confirm the progress stream advances through the LangGraph steps
3. Confirm preview rows render in the table output

This demonstrates the agent path:

- LangGraph plans the request
- the backend selects a visible MarcoPolo connection
- the backend invokes MarcoPolo MCP-backed commands
- the final response and preview rows are rendered in the chat UI

### 7. Configure and Test Other Connections

After Salesforce is working:

1. Use `Connections -> Connect a Data Source`
2. Enter a supported connection type such as `jira`
3. Complete the embedded setup flow
4. Click `Refresh`
5. Extend the integration examples or ask the Chatbot about the new connection

To add more SDK-driven examples, edit the SDK example definitions in:

- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/app/services/marcopolo.py`

### 8. Switch to WorkOS Connect

After the Developer API token path is working, request WorkOS Connect secrets from Immersa and configure:

- `WORKOS_API_KEY`
- `WORKOS_CONNECT_AUTH_URL`
- `WORKOS_CONNECT_CLIENT_ID`
- `WORKOS_CONNECT_CLIENT_SECRET`
- `WORKOS_CONNECT_REDIRECT_URI`
- `WORKOS_CONNECT_LOGIN_URI`

Then:

1. switch the auth mode to `WorkOS Connect Token`
2. enter any test email
3. complete the Connect authorization flow when prompted
4. repeat the same connection, integration, and chatbot validation

If Connect mode is correctly configured, the same app behaviors should work with a Connect-generated bearer token instead of the Developer API token.

## Next Reading

- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/docs/authentication-modes.md`
- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/docs/sdk-and-chatbot.md`
- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/docs/repo-map.md`
- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/docs/known-limitations.md`
