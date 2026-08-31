# Milestone 4 Learning Note: Fake Tools

The nine tools in this milestone are ordinary Python functions with Pydantic input and output models. That gives each tool a clear contract: callers know what information to provide and what information they will get back. The functions use fixed synthetic data, so tests never require an API key, an LLM, a local NERC document, or a live system.

Each tool has three fixtures in `tests/fixtures/fake_tool_fixtures.py`:

- **Success:** a known synthetic input that returns a typed result.
- **Empty result:** a valid request with no matching synthetic data, or a safe pause when no decision exists.
- **Error:** a deliberate `raise-error` input that raises `FakeToolError` so later graph work can practice error handling.

The classifications are important:

- **Read:** fetches synthetic records and cannot change data.
- **Read/compute:** turns supplied synthetic records into a draft or analysis; it still cannot change data.
- **Interrupt:** pauses for a future human decision without changing data.
- **Write:** the simulated workflow store. It writes only a JSON copy of approved synthetic state below `outputs/workflows/` and rejects every pending, rejected, or revise decision.

The local export is not an operational workflow, a compliance conclusion, or a real system change. It is a safe demonstration artifact.
