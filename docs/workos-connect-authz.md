# WorkOS Connect Standalone In This Demo

This document explains, step by step, how the Integration Demo uses **WorkOS Connect Standalone** to mint a MarcoPolo-compatible access token for the selected demo user.

This is not the same as using WorkOS as the demo app's primary login system.

The demo does two separate things:

1. It creates a local demo session for a "Test User" by impersonating an email address.
2. It uses WorkOS Connect Standalone to generate an OAuth access token for that already-selected user.

That second token is what the backend later uses when calling MarcoPolo.

## The WorkOS Standalone Idea

WorkOS Standalone Connect is designed for apps that already have their own authentication system. AuthKit redirects to a configured **Login URI** with an `external_auth_id`; your app authenticates the user in its own system, calls the WorkOS completion API, and WorkOS returns a `redirect_uri` that sends the browser back into the OAuth flow. After that, your redirect URI receives the authorization code, which your backend exchanges for tokens.

Reference: [WorkOS Standalone Connect](https://workos.com/docs/authkit/connect/standalone)

That pattern maps well to this demo because we already have a local demo session model based on a Test User email. We treat that demo session as the "existing authentication system" that WorkOS Standalone needs. The result is: WorkOS issues a token for the impersonated demo user, and the backend stores that token as the current user's MarcoPolo access token.

## What This Demo Is Doing

In this repository:

- the frontend lets the reviewer select `WorkOS Connect Token`
- the reviewer enters a Test User email
- the backend creates a local session for that email
- the frontend detects that the user is authenticated locally but does not yet have a MarcoPolo token
- the frontend redirects to `/api/auth/marcopolo/authorize`
- the backend starts the WorkOS Connect authorization flow
- WorkOS sends the browser to this app's Login URI with `external_auth_id`
- the backend completes the WorkOS Standalone handshake for the already-impersonated user
- WorkOS sends the browser back through the OAuth authorization flow
- the backend exchanges the returned code for tokens
- the access token is saved into the demo session and used for later MarcoPolo API and MCP calls

## Files To Read

These are the main implementation files:

- frontend runtime:
  - `frontend/src/auth/useAuthRuntime.ts`
  - `frontend/src/auth/AuthGateScreen.tsx`
  - `frontend/src/App.tsx`
- backend auth routes:
  - `backend/app/api/auth.py`
- backend auth/session service:
  - `backend/app/services/auth/service.py`
  - `backend/app/services/auth/session_store.py`
- backend config and auth-mode definitions:
  - `backend/app/core/config.py`
  - `backend/app/core/auth_modes.py`
- backend request/session reconstruction:
  - `backend/app/core/dependencies.py`
- backend MarcoPolo token use and refresh:
  - `backend/app/services/platform/marcopolo/session_manager.py`

## Required Configuration

The WorkOS-specific settings live in `backend/app/core/config.py`.

The important ones are:

- `WORKOS_CONNECT_AUTH_URL`
- `WORKOS_API_KEY`
- `WORKOS_CONNECT_CLIENT_ID`
- `WORKOS_CONNECT_CLIENT_SECRET`
- `WORKOS_CONNECT_REDIRECT_URI`
- `WORKOS_CONNECT_LOGIN_URI`

How they are used:

- `WORKOS_CONNECT_AUTH_URL`
  - the AuthKit domain used for `/oauth2/authorize` and `/oauth2/token`
- `WORKOS_API_KEY`
  - the server-side key used to call the WorkOS completion API
- `WORKOS_CONNECT_CLIENT_ID`
  - included in the authorize redirect and token exchange
- `WORKOS_CONNECT_CLIENT_SECRET`
  - used during token exchange and refresh
- `WORKOS_CONNECT_REDIRECT_URI`
  - the callback URI that receives the OAuth authorization code
- `WORKOS_CONNECT_LOGIN_URI`
  - the Login URI WorkOS should be configured to call for Standalone Connect

Important note:

- in this demo, the Login URI is conceptually `/api/auth/workos/login`
- the backend does not send `WORKOS_CONNECT_LOGIN_URI` on the authorize redirect
- instead, WorkOS uses the Login URI already configured for the Standalone Connect application
- `WORKOS_CONNECT_LOGIN_URI` is therefore documentation and environment coordination for the demo, while the active route implementation is `backend/app/api/auth.py -> /workos/login`

The `workos_connect` auth mode is defined in `backend/app/core/auth_modes.py`. Its description is intentionally explicit: this mode exists to mint a MarcoPolo-compatible access token for the selected demo user.

## End-To-End Flow

### Step 1: The browser loads runtime state

`frontend/src/auth/useAuthRuntime.ts` calls:

- `GET /api/config/public`
- `GET /api/auth/session`

This gives the frontend:

- the available MarcoPolo auth modes
- the currently selected mode
- whether the current user is authenticated
- whether the current user already has a provisioned MarcoPolo token

The frontend derives:

- `selectedMarcoPoloAuthMode`
- `usesWorkosConnect`
- `needsMarcoPoloAuthorization`

The crucial boolean is `needsMarcoPoloAuthorization`:

- user is authenticated locally
- selected mode is `workos_connect`
- `marcoPoloProvisioned` is still `false`

That boolean is what triggers the WorkOS redirect.

### Step 2: The reviewer selects `WorkOS Connect Token`

The mode picker lives in `frontend/src/auth/AuthGateScreen.tsx`.

When the mode changes, `useAuthRuntime.ts` posts to:

- `POST /api/auth/marcopolo/mode`

That route is implemented in `backend/app/api/auth.py` and handled by:

- `AuthPlatformService.set_selected_marcopolo_auth_mode(...)`

in `backend/app/services/auth/service.py`.

What this method does:

- stores the selected auth mode in the cookie-backed session
- reloads any existing auth payload from the in-memory session store
- normalizes the payload for the selected mode

The normalization logic is `_normalized_auth_payload_for_mode(...)`.

Important behavior:

- switching away from `workos_connect` clears stored WorkOS token fields
- switching to `workos_connect` keeps the user authenticated locally, but `marcopolo_provisioned` is only true if a MarcoPolo access token already exists

### Step 3: The reviewer creates the local demo session

The "Test User" form posts to:

- `POST /api/auth/impersonate`

That route calls:

- `AuthPlatformService.impersonate_user(...)`

This method:

- lowercases and validates the email
- creates a local `UserProfile`
- sets:
  - `provider = "impersonation"`
  - `subject = "impersonation:<email>"`
  - `email = <entered email>`
- writes an auth payload to the session store
- records the currently selected MarcoPolo auth mode
- sets `marcopolo_provisioned = False`

At this point:

- the user is authenticated in the demo
- the user does not yet have a MarcoPolo token

That is exactly the state needed for Standalone Connect.

### Step 4: The frontend notices that WorkOS authorization is needed

Back in `frontend/src/auth/useAuthRuntime.ts`, a `useEffect(...)` watches:

- `session.authenticated`
- `usesWorkosConnect`
- `needsMarcoPoloAuthorization`
- `config.marcoPolo.authModeConfigured`

When all of those line up, it redirects the browser to:

- `/api/auth/marcopolo/authorize?returnTo=<frontend-url>`

This is the entrypoint that starts WorkOS Connect.

### Step 5: The backend starts the OAuth authorization flow

`GET /api/auth/marcopolo/authorize` is handled by:

- `AuthPlatformService.authorize_marcopolo_connect(...)`

This method:

- confirms there is a locally authenticated user
- confirms the selected mode is `workos_connect`
- confirms the required WorkOS settings are present
- validates that the local user has an email address
- generates an OAuth `state`
- stores that `state` in `request.session`
- stores a `return_to` URL in `request.session`
- redirects the browser to the WorkOS authorize URL

The authorize URL is built by `_build_workos_connect_authorize_url(...)`.

It includes:

- `client_id`
- `redirect_uri`
- `response_type=code`
- `scope`
- `state`

This is the standard OAuth entrypoint into WorkOS Connect.

### Step 6: WorkOS redirects to the Login URI with `external_auth_id`

In Standalone Connect, if AuthKit needs your app to authenticate the user, it redirects to your configured Login URI and includes `external_auth_id`. Your app is expected to authenticate the user in its own system and then call the completion API with that `external_auth_id` and the user identity.

In this demo, the Login URI is:

- `/api/auth/workos/login`

That route reads `external_auth_id` from the query string and calls:

- `AuthPlatformService.handle_workos_connect_login(...)`

### Step 7: The backend completes the Standalone Connect handshake

`handle_workos_connect_login(...)` is the core of the Standalone integration.

It does the following:

1. Validates that `external_auth_id` is present.
2. Validates that the demo already has a locally authenticated user.
3. Reads the impersonated `UserSession`.
4. Builds a stable external user id:
   - `uid_<normalized-email>`
5. Builds the completion payload:
   - `external_auth_id`
   - `user.id`
   - `user.email`
   - `user.name`
   - optionally `first_name`
   - optionally `last_name`
6. Calls the WorkOS completion endpoint using `WORKOS_API_KEY`.
7. Reads `redirect_uri` from the WorkOS response.
8. Redirects the browser to that `redirect_uri`.

This matches the Standalone Connect contract: the app tells WorkOS which already-authenticated user corresponds to `external_auth_id`, and WorkOS returns a redirect back into the OAuth flow.

The important design point is that the impersonated Test User becomes the user identity that WorkOS Connect issues the token for.

### Step 8: WorkOS redirects back with an authorization code

After the Standalone completion step, WorkOS continues the OAuth flow and eventually redirects the browser to:

- `WORKOS_CONNECT_REDIRECT_URI`

In this demo that route is:

- `/api/auth/workos/callback`

The route calls:

- `AuthPlatformService.complete_workos_connect(...)`

This method:

- checks for OAuth errors
- validates the returned `state` against the value stored in session
- reads the authorization `code`
- exchanges the code at WorkOS `/oauth2/token`
- reads:
  - `access_token`
  - `refresh_token`
  - `id_token`
  - `token_type`
  - `expires_in`

### Step 9: The backend saves the token into the demo session

Still inside `complete_workos_connect(...)`, the backend reloads the current auth payload from the in-memory session store and writes:

- `marcopolo_access_token`
- `marcopolo_refresh_token`
- `marcopolo_id_token`
- `marcopolo_token_type`
- `marcopolo_expires_at`
- `marcopolo_auth_mode = "workos_connect"`
- `marcopolo_provisioned = True`

Then it redirects back to the original frontend URL stored in:

- `_WORKOS_CONNECT_RETURN_TO_SESSION_KEY`

At that point, the frontend can reload `/api/auth/session` and see that `marcoPoloProvisioned` is now true.

## How The Session Is Stored

The actual auth payload is not stored directly in the browser cookie.

The backend uses two layers:

1. `request.session`
   - cookie-backed session metadata
   - stores small values like:
     - selected auth mode
     - OAuth state
     - return URL
     - `auth_session_id`
2. `AuthSessionStore`
   - in-memory server-side store
   - keyed by `auth_session_id`
   - stores the full auth payload including WorkOS tokens

This logic lives in:

- `backend/app/services/auth/session_store.py`

So the browser cookie holds a pointer, and the in-memory store holds the sensitive token-bearing payload used to reconstruct `UserSession`.

## How Later MarcoPolo Calls Use The Token

Once the WorkOS flow completes, later backend calls do not talk to WorkOS again immediately.

Instead:

1. `backend/app/core/dependencies.py` reconstructs `UserSession` for each request.
2. MarcoPolo-backed services call `MarcoPoloSessionManager.resolve_session(...)`.
3. If the selected mode is `workos_connect`, the session manager uses `user_session.marcopolo_access_token`.

That logic lives in:

- `backend/app/services/platform/marcopolo/session_manager.py`

If the token is close to expiry, the session manager automatically uses `marcopolo_refresh_token` to call WorkOS `/oauth2/token` with `grant_type=refresh_token`, then persists the refreshed token fields back into the same auth session.

So the WorkOS token lifecycle is:

- initial token minted by authorization-code exchange
- refresh performed later on demand by the MarcoPolo session manager

## Minimal Sequence For Your Own App

If you want to implement the same pattern in your own app, the minimal sequence is:

1. Authenticate the user in your own app.
2. Keep enough local session state to know who the current user is.
3. Start WorkOS Connect authorization and store an OAuth `state`.
4. Configure a Login URI that can receive `external_auth_id`.
5. When WorkOS calls that Login URI:
   - resolve the current locally authenticated user
   - call the WorkOS Standalone completion API with:
     - `external_auth_id`
     - stable app-specific user id
     - user email
     - user name
6. Redirect the browser to the returned `redirect_uri`.
7. Handle the OAuth callback.
8. Exchange the authorization code for tokens.
9. Store the access token and refresh token in your app session or token store.
10. Use that access token for downstream API calls.
11. Refresh it later when necessary.

## Why This Works Well For The Demo

This repository intentionally avoids implementing a real login system. The impersonated Test User is enough to simulate the "existing authentication system" required by Standalone Connect.

That gives us a simple mental model:

- local demo auth chooses **which user**
- WorkOS Connect mints **that user's OAuth token**
- MarcoPolo services consume **that token**

That separation is the main idea new integrators should copy.
