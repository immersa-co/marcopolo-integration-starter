# Authentication Modes

The demo currently supports two MarcoPolo authentication modes.

## 1. Developer API Token

Use this first.

What it is:

- a Developer API token created from the MarcoPolo web app
- tied to an already provisioned MarcoPolo workspace

Why it exists:

- simplest path to validate integration
- easiest way to configure connections in a known workspace
- easiest way to verify SDK and Chatbot behavior

How the demo uses it:

1. the user selects `Developer API Token`
2. the user enters a Test User email
3. the backend ignores upstream identity for token minting
4. the backend uses `MARCOPOLO_DEVELOPER_API_TOKEN` directly for MarcoPolo calls

Important detail:

- for clarity during development, use the same email in the Test User field as the email that owns the MarcoPolo workspace behind the token

Required `.env` value:

- `MARCOPOLO_DEVELOPER_API_TOKEN`

## 2. WorkOS Connect Token

Use this after the Developer API token path is working.

What it is:

- a WorkOS Standalone Connect-based flow that yields a MarcoPolo-compatible bearer token

Why it exists:

- lets the demo test user-specific MarcoPolo access paths
- avoids using a single personal Developer API token for all users

How the demo uses it:

1. the user selects `WorkOS Connect Token`
2. the user enters a Test User email
3. the backend starts the Connect authorization flow
4. WorkOS returns tokens the backend stores in the session
5. the backend uses that access token for MarcoPolo API and MCP calls

Required `.env` values:

- `WORKOS_API_KEY`
- `WORKOS_CONNECT_AUTH_URL`
- `WORKOS_CONNECT_CLIENT_ID`
- `WORKOS_CONNECT_CLIENT_SECRET`
- `WORKOS_CONNECT_REDIRECT_URI`
- `WORKOS_CONNECT_LOGIN_URI`

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
