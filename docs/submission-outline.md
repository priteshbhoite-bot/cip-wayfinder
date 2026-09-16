# Product review outline

1. **Problem and user** — A local application for a compliance analyst reviewing a fictional cyber asset.
2. **Scope** — CIP-010-5 primary and CIP-007-6 supporting; no applicability or compliance conclusion.
3. **Architecture** — Show `docs/architecture.md`, the LangGraph workflow, tool boundary, local checkpointer, and approval interrupt.
4. **Agent framework and tools** — Explain the seven roles and nine tools using the agent framework and project brief.
5. **Data safety** — Show synthetic snapshots, approved-local-corpus provenance, untrusted evidence handling, and no-secret policy.
6. **End-to-end demo** — Follow `docs/demo-script.md`: failure, recovery, interrupt, human decision, approved local export, and traceability display.
7. **Verification** — Show the 15/15 offline evaluation report and the passing test suite.
8. **Limitations and next steps** — Explain the human review requirement, optional tracing, and the external-connection approval rule.
9. **Delivery** — The GitHub repository already exists. Review and publish the current tested source changes without credentials or generated outputs. Provide the final Google Doc, a live app-demo video under five minutes, and the GitHub link in the actual submission form. See `docs/final-readiness-check.md` for unresolved delivery gates. The Excel tutorial is not the app-demo recording.
