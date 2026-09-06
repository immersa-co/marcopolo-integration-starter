# How To Sanity Test

Use this smoke test after frontend or backend changes to confirm the app still works end to end against MarcoPolo production.

## Preconditions

- Backend is running on `http://localhost:8001`
- Frontend is running on `http://localhost:5173`
- `.env` points at MarcoPolo production endpoints
- `MARCOPOLO_NAMESPACE_KEY` is configured
- the namespace key came from the MarcoPolo team
- the selected demo email is a valid MarcoPolo production user
- `LLM_PROVIDER`, `LLM_MODEL`, `LLM_API_BASE_URL`, and `LLM_API_KEY` are configured

## Smoke Test Steps

1. Relaunch the frontend app if needed.
2. Open Chrome to `http://localhost:5173`.
3. In the auth mode selector, choose `Namespace key (recommended)`.
4. In the email field, enter a valid MarcoPolo user email such as `<user>@<domain>`.
5. Click `Create demo app session`.
6. Confirm the session strip shows resolved `namespace` and `company`.
7. Click the `Chatbot` tab.
8. In the chat composer, enter `List top 5 customers by revenue from Salesforce`.
9. Wait for the LangGraph agent to finish.
10. Confirm the chat shows a final result listing 5 customers.

Optional connection-management regression:

1. Open `Connections`.
2. Click `Add Data Source`.
3. Search for a provider such as `Jira` or `Google Drive`.
4. Confirm the right-hand provider detail updates when you click different providers.
5. Create or reauthorize a provider if test credentials are available.
6. Open `Manage` on an existing connection and confirm edit, test, and delete controls are present.

## Pass Criteria

- The namespace-key auth flow succeeds.
- The chatbot tab loads without errors.
- The LangGraph agent runs to completion.
- The final response contains 5 Salesforce customers ranked by revenue.
- The connection dialog can load provider metadata without stale detail state.
