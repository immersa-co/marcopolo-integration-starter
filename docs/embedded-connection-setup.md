# Embedded Connection Setup

This document is historical.

`marcopolo-integration-starter` no longer uses the embedded MarcoPolo MCP app host for connection creation or management.

That flow was removed after MarcoPolo deprecated the embedded setup path.

The current repo uses:

- backend SDK and API calls to list connection types
- backend-normalized setup metadata
- a frontend `Add Data Source` dialog that renders provider fields dynamically
- backend routes for create, edit, reauthorize, test, and delete

Use these docs instead:

- `docs/connection-setup-sdk-migration.md`
- `docs/repo-map.md`
- `README.md`
