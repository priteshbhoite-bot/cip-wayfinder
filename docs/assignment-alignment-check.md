# Week 3 assignment alignment check

## Overall assessment

**Strongly aligned as a code-track prototype.** The repository demonstrates the assignment's hard agentic-system requirements: a multi-step LangGraph workflow, typed state, tools with read/write classification, bounded recovery, a human approval interrupt, checkpointer and thread ID, local persistence/resume, tests, offline evaluations, an end-to-end demo script, and supporting documentation.

The remaining work is primarily submission and production-readiness evidence, not the core graph design.

## Requirement-to-evidence matrix

| Assignment expectation | Status | Repository evidence | What remains |
|---|---|---|---|
| A real, multi-step agentic task | Complete | `src/nerc_compliance_intelligence/review_graph.py`, `docs/architecture.md` | Use the supplied CIP documents in the recorded demo. |
| Code-track LangChain/LangGraph implementation | Complete | LangGraph `StateGraph`, `InMemorySaver`, `Command`, and `interrupt` usage | None for the prototype. |
| Specialized agents and orchestration | Complete | Six roles in `docs/agent-framework.md`; graph nodes coordinate the pipeline | Explain the roles briefly in the video. |
| Tools, with read vs. write boundaries | Complete | Nine typed tools and fixtures in `fake_tools.py`; only approved synthetic export is write-classified | None. |
| Stateful control flow and memory | Complete | Typed `AgentState`, `thread_id`, checkpointer, and SQLite resume tests | None. |
| Error handling and recovery | Complete | Empty retrieval, error, retry, repair, safe-stop, edit, reject, and approve branch tests | Demonstrate failure and recovery in the video. |
| Human-in-the-loop before a write | Complete | LangGraph interrupt plus export guard; app decision preview does not bypass it | Demonstrate approve/edit/reject in the video. |
| Tracing and evaluations | Complete for offline mode | 15 deterministic evaluations and safe LangSmith configuration preview | Optional: approved, cost-bounded live tracing run. |
| Simple interface | Complete | Upload-first Streamlit interface with collapsed requirement summaries, draft review sections, and a human package decision | Show it live in the video. |
| Project documentation | Substantially complete | Architecture, agent framework, data notes, prompt log, limitations, demo script, and this check | Assemble the requested material into one final Google Doc if that is the required submission format. |
| Five-minute-or-less video demo | Not yet evidenced | `docs/demo-script.md` and ElevenLabs brief prepare the content | Record and save the final video. |
| GitHub code link or ZIP | In progress | The public repository exists and the reviewed release changes are prepared as one local commit | Push the prepared commit after a final human check, or prepare a ZIP. |
| At least one real model call | Partial / optional decision | Provider abstraction supports Nebius or Fireworks preview, but live calls are intentionally blocked pending explicit approval | If the instructor requires a real call, review the exact preview and explicitly authorize a tiny paid smoke test. |

## Framework completeness

The assignment's framework asks for a one-line goal, surface, steps, tools, memory, hard limits, human handoff, failure behavior, and a success measure.

- **Goal and user:** defined in `docs/project-brief.md`; a compliance analyst reviews a scoped CIP standard.
- **Surface:** Streamlit web interface.
- **Steps and orchestration:** diagram and control flow in `docs/architecture.md`.
- **Tools:** nine typed local tools with success, empty, and error fixtures.
- **Memory:** browser-session upload state, `thread_id` plus `InMemorySaver`, and approval-gated SQLite case resume.
- **Hard limits:** no compliance declaration, legal advice, confidential/live IT/OT data, uncontrolled external calls, or operational writes.
- **Human handoff:** interrupt before guarded export; edit/reject routes are explicit.
- **Failure behavior:** retry at most twice, repair at most once, otherwise safe stop.
- **Success measure:** all 15 offline evaluations pass, and a reviewer can complete the scripted review without bypassing human approval.

## Recommended submission order

1. Refresh the Streamlit app and use one of the supplied public CIP PDFs.
2. Follow `docs/demo-script.md`: show missing retrieval failure, recovery, graph interrupt, a human decision, and guarded approved export.
3. Record the live walkthrough in under five minutes.
4. Create one final project document from the existing architecture, data notes, prompt log, evaluation report, and lessons learned.
5. Review the prepared local commit, then explicitly approve either pushing it to GitHub or creating a ZIP submission.
6. If a live-model call is required, first review the exact Nebius/Fireworks request and cost-sensitive scope; do not add a credential or call the provider until that approval is given.
