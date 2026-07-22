# SDK and Chatbot Guide

The demo intentionally shows two different MarcoPolo consumption patterns.

## 1. SDK Path: Traditional Product Integration

The `Integrations` tab demonstrates the non-agent path using `marcopolo-sdk`.

References:

- GitHub: `https://github.com/immersa-co/marcopolo-python-sdk`
- PyPI: `https://pypi.org/project/marcopolo-sdk/`

Use this when:

- a product feature needs deterministic data access
- an AI agent runtime is unnecessary
- the application wants to render tables, KPIs, or workflow results directly

Current implementation entrypoint:

- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/app/services/marcopolo.py`

Flow:

1. resolve the active MarcoPolo auth mode
2. construct a MarcoPolo session
3. call `list_connections`
4. choose the first matching connection for the example
5. call `marcopolo-sdk` `execute(...)`
6. return preview rows to the frontend

Why this matters:

- it shows how a normal application backend can call MarcoPolo without adopting MCP directly in every feature

## 2. Agent Path: MCP Tools Through LangGraph

The `Chatbot` tab demonstrates an agent flow that uses MarcoPolo MCP tools.

Current implementation entrypoints:

- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/app/services/langgraph_agent.py`
- `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/app/services/marcopolo.py`

Flow:

1. accept a natural-language prompt
2. inspect visible connections
3. pick the best matching connection
4. choose a mode such as `browse` or `query`
5. invoke MarcoPolo MCP-backed commands
6. render final text and preview rows in the UI

Why this matters:

- it shows how an AI agent can use MarcoPolo as the data and tool layer

## How to Extend the Integrations Tab

To add new examples:

1. add a new `DataConnectionOperationSpec` in `https://github.com/immersa-co/marcopolo-integration-starter/blob/main/backend/app/services/marcopolo.py`
2. provide:
   - title
   - prompt
   - target connector type
   - runtime matching terms
   - query payload
3. reload the backend
4. verify the new example appears in `Integrations`

Important design choice:

- the demo resolves the first matching connection at runtime instead of hardcoding one connection slug

That makes the examples more stable across different workspaces.

## Recommended First Validation

1. install the Salesforce demo connection
2. run the Salesforce integration example
3. ask the Chatbot a Salesforce question
4. add Jira
5. add a Jira integration example or ask the Chatbot about Jira
