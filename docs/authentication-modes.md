# Authentication Modes

The partner namespace E2E path is WorkOS Connect. The Test User field remains a local demo harness for the
partner application's authenticated user; it is not a replacement for WorkOS authentication.

## 1. WorkOS Connect (partner E2E)

What it is:

- a WorkOS Standalone Connect flow that yields a user bearer token from the partner's AuthKit environment

Why it exists:

- lets Marcopolo verify the partner issuer and resolve the correct namespace and company
- avoids using a personal Marcopolo Developer API token for partner users

How the demo uses it:

1. the user selects `WorkOS Connect (partner E2E)`
2. the user enters the partner application's user as a Test User
3. the backend starts WorkOS Connect authorization
4. after the authorization code exchange, the backend calls `POST http://localhost:8000/api/auth/bootstrap`
   with the WorkOS access token and refresh token
5. the backend accepts the flow only when bootstrap returns `success: true` and
   `data.redirect_url`, `data.company`, and `data.namespace`
6. the session stores the authoritative `company` and `namespace` returned by Marcopolo
7. MarcoPolo API and MCP calls use the WorkOS access token; they do not fall back to a developer token

The starter never derives `company` from the Test User email, parses unverified JWT claims, or sends a namespace
chosen by the starter. Marcopolo resolves the namespace from the verified WorkOS issuer.

Required `.env` values:

- `WORKOS_CONNECT_AUTH_URL`
- `WORKOS_CONNECT_CLIENT_ID`
- `WORKOS_CONNECT_CLIENT_SECRET`
- `WORKOS_CONNECT_REDIRECT_URI`

For the local Entelligence E2E, `.env.example` supplies the documented AuthKit domain and client ID. Secret values
remain empty and must be filled locally.

## 2. Developer API Token (local shortcut only)

This mode is retained for quickly inspecting an already provisioned local workspace. It is not a partner integration
and must not be used to validate namespace resolution or the Entelligence E2E flow.

Required `.env` value:

- `MARCOPOLO_DEVELOPER_API_TOKEN`

## Deliberate Demo Simplification

This repository does **not** implement a real customer login system.

Instead:

- the app uses a Test User email field
- the backend session is local and in-memory
- the purpose is to make MarcoPolo integration seams easy to inspect

Production customers should replace this with:

- their own authentication mechanism
- their own session store
- their own decision about how to bind platform users to MarcoPolo access
