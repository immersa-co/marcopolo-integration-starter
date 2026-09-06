# Connection Setup SDK Migration

This note records the completed migration away from the deprecated embedded MarcoPolo MCP app connection setup flow.

The current starter uses backend SDK and API calls only.

## What Changed

The old approach depended on:

- an embedded MarcoPolo MCP app
- iframe host wiring
- embedded OAuth continuation
- ext-app proxying and session-resume behavior

That flow is no longer used.

The current implementation uses the latest `marcopolo-sdk` package from PyPI plus normalized backend routes.

## Current User Experience

The `Connections` tab now exposes two distinct flows:

- `Install Demo Data`
  - installs a hosted demo connection quickly for testing
- `Add Data Source`
  - opens a dynamic dialog driven by MarcoPolo connection-type metadata

The same section also supports managing existing connections:

- edit connection
- reauthorize OAuth connection
- test connection
- delete connection

## Current Backend Contract

The frontend does not depend directly on raw SDK models. The backend exposes a stable normalized contract instead.

### Discovery

- `GET /api/connections`
- `GET /api/connections/types`
- `GET /api/connections/types/{connection_type}`

### Create

- `POST /api/connections`
- `POST /api/connections/oauth-setup`
- `GET /api/connections/oauth-setup/{setup_session_id}`

### Manage Existing Connections

- `GET /api/connections/{connection_name}`
- `PATCH /api/connections/{connection_name}`
- `POST /api/connections/{connection_name}/reauthorize`
- `POST /api/connections/{connection_name}/test`
- `DELETE /api/connections/{connection_name}`

### Demo Install

- `POST /api/connections/demo-install`

## SDK Surfaces Used

The migration is built on these `marcopolo-sdk` surfaces:

- `client.workspace.connections()`
- `client.connection_types.list(...)`
- `client.connection_types.get(connection_type)`
- `client.connections.create(...)`
- `client.connections.get(...)`
- `client.connections.get_configuration(...)`
- `client.connections.update(...)`
- `client.connections.delete(...)`
- `client.connections.test(connection_name)`
- `client.connection_setup.start(...)`
- `client.connection_setup.get(setup_session_id)`

## Frontend Behavior

The `Add Data Source` dialog now:

1. searches connection types through the backend
2. loads selected provider detail dynamically
3. renders setup-method choices
4. renders supported field widgets from provider metadata
5. starts hosted OAuth when needed
6. refreshes the connection list after success

The `Manage` flow now:

1. loads the selected connection
2. shows editable configuration
3. supports field updates
4. supports OAuth reauthorization
5. supports test and delete

## What Was Removed

No production code path now depends on:

- embedded ext-app HTML
- iframe host context injection
- ext-app proxy routes
- embedded OAuth message hydration
- embedded setup-session resume caches

## Remaining Constraints

The current dialog intentionally supports the common setup-field shapes first:

- string
- number
- integer
- boolean
- arrays of simple scalar values
- hosted OAuth setup methods

Providers that require richer nested objects or file-upload widgets may still need additional UI work.
