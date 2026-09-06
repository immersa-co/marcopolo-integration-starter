# Developer Guide

This guide is the recommended onboarding path for `marcopolo-integration-starter`.

## What This Demo Shows

- how to mint a MarcoPolo user token from a configured namespace key after the partner app authenticates its user
- how the session exposes MarcoPolo's resolved namespace and company
- how to manage MarcoPolo connections from a custom web app using backend SDK and API calls
- how to use the latest `marcopolo-sdk` package from PyPI for traditional product integrations
- how to use raw MarcoPolo MCP tools from an MCP-only LangGraph agent
- how to switch the LangGraph agent between OpenAI and Anthropic using `LLM_PROVIDER`

## Recommended Learning Path

### 1. Get the App Running

1. Copy `.env.example` to `.env`.
2. Fill the required production settings.
3. Ask the MarcoPolo team for `MARCOPOLO_NAMESPACE_KEY`.
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

6. Open `http://localhost:5173`.
7. Choose `Namespace key (recommended)`.
8. Create a demo app session for a valid MarcoPolo production user.
9. Confirm the session strip shows the resolved `namespace` and `company`.

The demo app session represents a user the partner application has already authenticated. In the recommended mode, the backend exchanges the configured namespace key for a short-lived user token, validates the MarcoPolo response, and stores the returned namespace and company.

### 2. List Available Connections

After namespace resolution succeeds, open the `Connections` tab and click `Refresh`. The backend uses the resolved MarcoPolo user token and the UI renders the visible namespace connections.

### 3. Create or Install a Connection

You have two fast paths:

1. `Install Demo Data`
   - install a known-good demo connection such as Salesforce
2. `Add Data Source`
   - search for a provider
   - inspect the provider metadata
   - create the connection through fields or hosted OAuth

This is the fastest way to get a known-good connection for testing both SDK and agent flows.

### 4. Manage Existing Connections

The `Connections` tab now demonstrates the full supported connection-management loop:

- create connection
- edit connection configuration
- reauthorize OAuth connections
- test connection
- delete connection

This is all driven from backend-normalized SDK/API contracts rather than the removed embedded MCP app flow.

### 5. Understand `marcopolo-sdk`

The backend uses the published `marcopolo-sdk` package from PyPI for product-style integrations.

References:

- GitHub: `https://github.com/immersa-co/marcopolo-python-sdk`
- PyPI: `https://pypi.org/project/marcopolo-sdk/`

Relevant implementation:

- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/app/services/platform/marcopolo/service.py`

The important flow is:

1. build a MarcoPolo bearer token for the selected auth mode
2. construct the SDK client
3. select an available connection at runtime
4. call the SDK operation
5. render the returned rows in the app UI

This is the pattern to follow for non-agent features in a product.

### 6. Use the Integrations Section

In `Integrations`:

1. click a prompt such as the Salesforce example
2. confirm rows render in the result table

This demonstrates a product feature invoking MarcoPolo through `marcopolo-sdk` without involving the Chatbot or LangGraph.

### 7. Use the Chatbot

In `Chatbot`:

1. ask a question such as `List top 5 customer accounts by revenue from Salesforce.`
2. confirm the progress stream advances through tool-selection and tool-return status events
3. confirm preview rows render in the table output

This demonstrates the agent path:

- the backend opens a direct MCP session to MarcoPolo
- LangGraph runs a tool-calling loop over the raw MarcoPolo MCP tools
- the model can use `workspace_shell` and other exposed MCP tools directly
- the backend normalizes nested `workspace_shell` results into preview rows
- the final response and preview rows are rendered in the chat UI

### 8. Choose the LLM Provider

The chatbot runtime supports:

- `LLM_PROVIDER=openai`
- `LLM_PROVIDER=anthropic`

Required companion settings:

- `LLM_MODEL`
- `LLM_API_BASE_URL`
- `LLM_API_KEY`

The provider switch is implemented in the LangGraph runtime, so the same MarcoPolo MCP flow can be exercised against either provider.

## Next Reading

- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/docs/partner-namespace-manual-e2e.md`
- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/docs/authentication-modes.md`
- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/docs/connection-setup-sdk-migration.md`
- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/docs/sdk-and-chatbot.md`
- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/docs/repo-map.md`
- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/docs/known-limitations.md`
- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/docs/how-to-sanity-test.md`
