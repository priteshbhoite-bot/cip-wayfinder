# Milestone 13D — Offline evaluations and optional tracing preview

`evaluations.py` runs fifteen deterministic checks using only local fake data and temporary test SQLite storage. It returns a Markdown table with a short proof for each result. It catches unexpected errors and replaces them with a generic safe result; it does not print stack traces, prompts, tokens, or source-document text.

`tracing.py` supports a non-secret LangSmith preview using `NCI_LANGSMITH_TRACING` and `NCI_LANGSMITH_PROJECT`. It deliberately does not read `LANGSMITH_API_KEY`, initialize a LangSmith client, or send a trace. A later live tracing step must show the project, credential-variable name, and data scope, then receive explicit approval before any external connection.

Run the offline evaluation table:

```powershell
uv run python -m nerc_compliance_intelligence.evaluations
```
