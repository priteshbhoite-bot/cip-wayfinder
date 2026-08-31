# Milestone 9 Learning Note: Providers

The provider layer separates the rest of the application from any one model vendor. The default is `FakeStructuredProvider`, which returns a prewritten Python dictionary and validates it against a Pydantic output model. This lets tests confirm the same structured-output behavior without spending money or using an API key.

`NCI_MODEL_PROVIDER`, `NCI_MODEL_NAME`, `NCI_MODEL_TIMEOUT_SECONDS`, and `NCI_MODEL_MAX_RETRIES` are non-secret environment settings. The Nebius adapter uses `NCI_NEBIUS_API_KEY` only when explicitly constructed, never prints or stores it, and sends schema-constrained JSON to Nebius AI Studio's OpenAI-compatible chat endpoint. Set `NCI_MODEL_NAME` to a model available and approved in your Nebius account; model availability and pricing are account-specific.

Retries apply only to temporary errors and timeouts. The maximum is two retries after the first attempt. The fake timeout is immediate and deterministic, so tests do not wait.

Before a paid live smoke test, call `build_live_smoke_preview()`. It produces the exact request, selected model, credential-variable name, and cost-sensitive scope. The live provider function is deliberately blocked until the user reviews that preview and explicitly approves the request.
