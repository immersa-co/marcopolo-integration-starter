# How To Sanity Test

Use this smoke test after frontend or backend changes to confirm the app still works end to end.

## Preconditions

- Backend is running on `http://localhost:8001`
- Frontend is running on `http://localhost:5173`
- The environment is configured so WorkOS Connect can complete successfully

## Smoke Test Steps

1. Relaunch the frontend app if needed.
2. Open Chrome to `http://localhost:5173`.
3. In the auth mode selector, choose `WorkOS Connect Token`.
4. In the email field, enter `sameer@immersa.co`.
5. Click `Test User`.
6. Click the `Chatbot` tab.
7. In the chat composer, enter `List top 5 customers by revenue from Salesforce`.
8. Wait for the LangGraph agent to finish.
9. Confirm the chat shows a final result listing 5 customers.

## Pass Criteria

- The auth flow succeeds.
- The chatbot tab loads without errors.
- The LangGraph agent runs to completion.
- The final response contains 5 Salesforce customers ranked by revenue.
