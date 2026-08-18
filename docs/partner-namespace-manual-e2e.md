# Partner Namespace Manual E2E

This is the manual validation path for the Entelligence partner namespace. The partner application authenticates
the user first; WorkOS Standalone Connect then authorizes MarcoPolo access.

## Setup

1. Start the local Marcopolo stack at `http://localhost:8000`.
2. Copy `.env.example` to `.env`.
3. Fill the empty session, WorkOS, and application secret values. Keep the documented AuthKit domain and client ID.
4. Start the starter backend on `http://localhost:8001` and frontend on `http://localhost:5173`.

## Authentication

1. Open `http://localhost:5173`.
2. Select `WorkOS Standalone Connect (recommended)`.
3. Create a demo app session for a user the partner application has already authenticated.
4. Complete the Entelligence WorkOS Standalone Connect flow.

The backend exchanges the authorization code, then calls:

```text
POST http://localhost:8000/api/auth/bootstrap
Authorization: Bearer <WorkOS access token>
```

The request also includes the WorkOS refresh token. Bootstrap must return `success: true` and
`data.redirect_url`, `data.company`, and `data.namespace`. The starter stores the returned company and namespace
only after this validation succeeds.

## Expected result

The session strip must clearly show:

- `namespace: entelligence`
- `company: entelligence-demo`

The same values must be present in `GET http://localhost:8001/api/auth/session` as `namespace` and `company`, with
`marcoPoloProvisioned: true`.

After that, refresh the Connections tab and exercise the SDK and Chatbot examples. They must use the WorkOS Standalone Connect
session. A Marcopolo developer token is only a local shortcut and is not valid evidence for this partner E2E.

## Failure checks

- A bootstrap HTTP or response-contract failure must return a useful error.
- The session must remain unprovisioned after bootstrap failure.
- Logout or a session reset must clear `namespace` and `company`.
- The starter must not derive `company` from an email, parse unverified JWT claims, or send a starter-selected
  namespace.
