# Partner Namespace Manual E2E

This is the manual validation path for the production partner namespace flow.

The partner application authenticates the user first. The starter then uses a MarcoPolo-issued namespace key to obtain a short-lived MarcoPolo user token for that same user.

## Setup

1. Copy `.env.example` to `.env`.
2. Fill the production endpoint values:
   - `MARCOPOLO_MCP_URL`
   - `MARCOPOLO_API_BASE_URL`
   - `MARCOPOLO_WEB_BASE_URL`
3. Ask the MarcoPolo team for `MARCOPOLO_NAMESPACE_KEY`.
4. Fill the required LLM settings for the chatbot:
   - `LLM_PROVIDER`
   - `LLM_MODEL`
   - `LLM_API_BASE_URL`
   - `LLM_API_KEY`
5. Start the backend on `http://localhost:8001`.
6. Start the frontend on `http://localhost:5173`.

## Authentication

1. Open `http://localhost:5173`.
2. Select `Namespace key (recommended)`.
3. Create a demo app session for a user the partner application has already authenticated.

The frontend then redirects to:

```text
GET /api/auth/marcopolo/authorize?returnTo=http://localhost:5173/
```

The backend exchanges the configured namespace key for a short-lived user token using the selected user's email. After success, it stores:

- `marcopolo_access_token`
- `marcopolo_expires_at`
- `company`
- `namespace`

## Expected Result

The session strip must clearly show:

- a resolved `namespace`
- a resolved `company`

The same values must be present in:

```text
GET http://localhost:8001/api/auth/session
```

as `namespace` and `company`, with `marcoPoloProvisioned: true`.

After that:

1. refresh the `Connections` tab
2. exercise `Add Data Source` or `Manage`
3. run an `Integrations` example
4. run a `Chatbot` prompt

All of those paths must use the namespace-key-issued user token.

## Failure Checks

- A namespace-key exchange failure must return a useful error.
- The session must remain unprovisioned after exchange failure.
- Logout or a session reset must clear `namespace` and `company`.
- The starter must not derive `company` or `namespace` from the email address.
- A developer API token must not be treated as proof that partner namespace routing works.
