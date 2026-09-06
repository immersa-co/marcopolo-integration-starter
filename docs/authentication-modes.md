# Authentication Modes

The demo app-session form represents a user the partner application has already authenticated. It is not a login system or a replacement for the partner's authentication.

The current starter exposes two MarcoPolo auth modes.

## 1. Namespace Key (recommended)

What it is:

- a MarcoPolo-issued namespace key held by the partner backend
- exchanged for a short-lived user token for the currently selected demo user

Why it exists:

- it is the intended partner integration path for this starter
- it lets MarcoPolo resolve the authoritative namespace and company for the selected user
- it avoids binding the demo to one developer workspace token

How the demo uses it:

1. the user selects `Namespace key (recommended)`
2. the user creates a demo app session for a user the partner application already authenticated
3. the frontend redirects to `GET /api/auth/marcopolo/authorize`
4. the backend exchanges `MARCOPOLO_NAMESPACE_KEY` for a short-lived user token by calling the namespace SDK client
5. the backend stores:
   - `marcopolo_access_token`
   - `marcopolo_expires_at`
   - `company`
   - `namespace`
6. MarcoPolo API and MCP calls use that issued user token

Required `.env` value:

- `MARCOPOLO_NAMESPACE_KEY`

Important note:

- ask the MarcoPolo team for a valid `MARCOPOLO_NAMESPACE_KEY`

## 2. Developer API Token (local shortcut only)

This mode is retained for quickly inspecting an already provisioned workspace. It is not the partner integration path and must not be used as evidence that namespace-key user routing works correctly.

Required `.env` value:

- `MARCOPOLO_DEVELOPER_API_TOKEN`

## Deliberate Demo Simplification

This repository does **not** implement a real customer login system.

Instead:

- the app uses a demo app-session email field
- the backend session is local and in-memory
- the purpose is to make MarcoPolo integration seams easy to inspect

Production customers should replace this with:

- their own authentication mechanism
- their own session store
- their own decision about how to bind platform users to MarcoPolo access
