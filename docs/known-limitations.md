# Known Limitations

## 1. Create Connection Only

The current embedded connection flow supports creating connections.

Not yet supported in this demo:

- edit an existing connection
- test an existing connection from the embedded detail view

Those are next on the roadmap.

## 2. Embedded MCP App Is the Current Connection UX

The current demo uses the embedded MarcoPolo MCP app for connection configuration.

If that approach is not desirable for a product:

- a dedicated MarcoPolo connection-management API
- and a custom application-owned UI

are the alternative direction on the roadmap.

## 3. Google Drive Configuration Is Not Yet Working

Google Drive embedded setup is intentionally not part of the stable demo baseline.

Reason:

- Google Picker introduces additional popup and post-auth continuation complexity that is not yet stable in the embedded host flow

For the stable demo path, use:

- Salesforce
- Jira
- other non-Google connections that do not require the same Picker continuation model
