# Known Limitations

## 1. Dynamic Setup Field Support Is Still Incremental

The current demo renders connection forms from MarcoPolo connection-type metadata.

The current implementation supports the common field shapes needed for the main providers:

- string
- number and integer
- boolean
- array values
- hosted OAuth setup methods

If a provider depends on richer nested objects, file uploads inside the setup flow, or more specialized widgets, the dialog may still need provider-specific follow-up work.

## 2. The Demo Session Model Is Intentionally Simple

The app still uses:

- a demo email field
- an in-memory local session
- a thin backend wrapper around MarcoPolo

That is appropriate for an integration reference app, but it is not a production-ready auth or session architecture.

## 3. Chatbot Quality Depends On External LLM Provider Configuration

The LangGraph runtime now supports both OpenAI and Anthropic through `LLM_PROVIDER`, but the demo still depends on:

- a valid model name
- a reachable provider endpoint
- an API key with quota

If those are misconfigured, the chatbot will fail before any MarcoPolo tool call.

## 4. Some Provider UX Still Needs More Depth

The current implementation proves the SDK/API-driven connection-management pattern, including create, edit, reauthorize, test, and delete.

Some providers may still benefit from:

- richer validation
- provider-specific help text
- more polished advanced-field widgets
- more guided error recovery
