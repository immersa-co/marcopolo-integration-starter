# Embedded Connection Setup

This document explains how `marcopolo-integration-starter` lets a user configure new MarcoPolo data connections from inside the integration app without treating MarcoPolo Web UI as the primary product surface.

## Prerequisites

This guide assumes working familiarity with:

- React
- TypeScript and JSX
- browser embedding concepts such as iframes and popups
- OAuth authorization flow basics for browser-based applications, especially popup and redirect handling
- basic MCP concepts, especially MCP apps and host-rendered app flows

Without that background, the embedded host bridge and OAuth continuation flow will be harder to follow in code.

## Problem Statement

An application integrating with MarcoPolo often wants users to:

- configure their own data connections
- stay inside the integrating application
- avoid being sent into MarcoPolo Web UI as the main experience

The goal is not to remove MarcoPolo from the system.

The goal is to let the integration app remain the system of engagement while MarcoPolo remains the system of record for:

- connection definitions
- connector auth flows
- saved configuration
- workspace-level execution

## Two Integration Options

There are two reasonable ways to offer connection configuration inside a customer application.

### Option 1. MarcoPolo API + WebUI Component Library

In this model, MarcoPolo would expose:

- a stable connection-management API
- a reusable UI component library or design system primitives

The integrating application would:

- call MarcoPolo APIs directly
- compose or skin its own connection configuration UX
- own more of the presentation and interaction flow

Why this is attractive:

- highest UX control for the integrating product
- easiest to make deeply native to the host application
- clearer long-term path for edit, test, and permissions workflows

Why it is not the first path in this demo:

- it requires more product surface from MarcoPolo
- it was not the fastest proven route when this demo was built

### Option 2. Embeddable MarcoPolo MCP App

In this model, MarcoPolo offers the connection configuration dialog itself as an embeddable MCP app.

The integrating application:

- hosts the MCP app inside its own UI
- passes the requested connection type and host context
- lets the MCP app drive the connection setup flow
- keeps the user in the integration app

Why this was chosen first:

- it already existed in working form
- it was already proven in MCP app hosts such as Claude Desktop
- it provided the fastest route to a real embedded connection setup experience

This demo therefore implements Option 2 first.

MarcoPolo still intends to offer Option 1 for comparison and for teams that want a more application-owned UX.

## MCP App Concept Overview

MarcoPolo exposes a `connection_setup` experience as an MCP app-style UI surface.

In a host such as Claude Desktop, that app is rendered by the host and can:

- collect connection configuration
- launch connector auth flows
- persist the resulting connection into the user’s MarcoPolo workspace

This demo applies the same idea in a custom web application.

Conceptually:

1. the integration app acts as the MCP app host
2. MarcoPolo provides the app payload and related widget metadata
3. the host renders that app inside its own container
4. the user completes connection setup from the host application
5. the saved connection still lives in the MarcoPolo workspace

So the UX appears embedded in the host app, but the configuration remains backed by MarcoPolo.

For background on MCP app concepts, refer to the official MCP app documentation used by your chosen host/runtime.

## Why This Demo Chose the MCP App Path First

This demo is meant to help developers understand integration seams quickly.

The embeddable MCP app path was the fastest way to prove:

- in-app connection configuration
- MarcoPolo-owned connection persistence
- support for both simple credential forms and OAuth-backed connectors

It is therefore the best first demonstration, even though it is not necessarily the final product shape for every customer.

## Implementation Walkthrough

This section maps the embedded flow to the codebase.

### Frontend host container

The host container lives in:

- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/frontend/src/EmbeddedConnectionSetupHost.tsx`

This component is responsible for:

- creating the iframe host surface
- connecting the app bridge
- passing the initial connection-setup payload into the embedded app
- opening popups for OAuth-style flows
- polling setup-session state when embedded continuation is required
- refreshing the connection list after success

### Launching the embedded setup

The main application flow lives in:

- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/frontend/src/connections/ConnectionsTab.tsx`
- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/frontend/src/connections/useConnectionsFeature.ts`

The user flow is:

1. open the `Connections` tab
2. choose `Connect a Data Source`
3. enter a supported connection type such as `jira`, `salesforce`, or `postgres`
4. the frontend asks the backend to start embedded connection setup

### Backend setup orchestration

The backend routes live in:

- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/app/api/connections.py`

The MarcoPolo integration layer lives in:

- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/app/services/platform/marcopolo/service.py`

The backend:

1. resolves the active MarcoPolo auth mode
2. creates a MarcoPolo session for the selected user
3. calls the MarcoPolo `connection_setup` tool
4. injects embedded host context such as:
   - `host_mode`
   - `host_return_url`
   - `host_origin`
   - `host_session_id`
5. rewrites the returned widget API base URL so subsequent embedded requests flow back through the demo backend proxy
6. returns the embedded payload to the frontend host

### Rendering and saving the connection

Once the embedded app is running:

- the user fills in the connector-specific form
- the embedded app performs the connector setup steps
- successful completion persists the connection into the user’s MarcoPolo workspace

After success, the host app refreshes the visible connection list through the normal `list_connections` flow.

That means the integration app does not persist connection definitions locally.

MarcoPolo remains the source of truth.

## OAuth-Specific Considerations

OAuth-backed connectors are more complex than simple form-based connectors because authorization temporarily leaves the embedded frame.

The host must support:

- opening the provider auth window or popup
- preserving the setup session
- resuming the embedded flow after OAuth returns
- refreshing the connection list only once the setup session is terminal

In this demo, that logic is implemented through:

- popup handling in the frontend host
- embedded setup-session lookup and polling
- OAuth proxying through the backend

Relevant code:

- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/frontend/src/EmbeddedConnectionSetupHost.tsx`
- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/app/api/connections.py`
- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/app/services/platform/marcopolo/service.py`

### Google Drive special case

OAuth connectors are generally compatible with the embedded pattern, but Google Drive is not yet part of the stable demo path.

Reason:

- after Google OAuth, Google Drive requires an additional Google Picker interaction
- that post-auth popup and continuation flow is more complex than simpler OAuth connectors
- it is not yet stable enough in this embedded host demo

So for the stable demo path, use connectors such as:

- Salesforce
- Jira
- other connectors that do not require the additional Google Picker continuation model

Google Drive remains on the roadmap.

## Limitations

Today this embedded MCP app approach supports:

- creating new connections

It does not yet demonstrate:

- editing an existing connection
- testing an existing connection from the embedded detail view
- connection permissions or sharing management

Those are product roadmap items rather than architectural dead ends.

## Roadmap

The likely next steps are:

- support edit/update flows for existing connections
- add `Test Connection` support
- add permissions and sharing UX when customer demand justifies it
- offer a direct MarcoPolo API + component-library approach so customers can compare it against the MCP app approach

## Recommended Reading

- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/docs/README.md`
- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/docs/repo-map.md`
- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/docs/known-limitations.md`
