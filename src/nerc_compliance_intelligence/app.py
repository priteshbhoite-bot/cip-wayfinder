"""Input-first Streamlit interface for the local, synthetic-data application."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from time import sleep
from typing import Any

import streamlit as st

from nerc_compliance_intelligence.baseline_analysis import analyze_baseline, load_expected_snapshots, load_observed_snapshots
from nerc_compliance_intelligence.case_intake import CaseIntake, CaseIntakeAssessment, assess_case_intake
from nerc_compliance_intelligence.config import AppSettings, load_settings
from nerc_compliance_intelligence.control_remediation import ControlGenerationInput, build_source_grounded_control_draft_request, generate_draft_control_and_remediation, generate_source_grounded_control_draft
from nerc_compliance_intelligence.evidence_analysis import EvidenceAnalysisInput, SyntheticEvidenceDocument, analyze_evidence
from nerc_compliance_intelligence.local_corpus import LocalCorpusStore, RequirementChunk, RetrievalQuery, chunk_to_mapping
from nerc_compliance_intelligence.reference_options import load_nerc_reference_options
from nerc_compliance_intelligence.review_graph import compact_graph_summary
from nerc_compliance_intelligence.providers import ProviderResponseError, ProviderTemporaryError, ProviderTimeoutError, build_nebius_provider_from_environment, load_local_provider_environment, load_provider_settings
from nerc_compliance_intelligence.uploaded_standard import UploadValidationError, UploadedStandard, analyze_uploaded_standard, validate_uploaded_standard


SCREEN_NAMES = ("Start a review", "Review package")
ANALYSIS_OPTIONS = (
    "Understand the requirement",
    "Create draft controls",
    "Review synthetic evidence and baseline",
    "Review findings and remediation",
)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
APP_LOGO_PATH = PROJECT_ROOT / "assets" / "cip-wayfinder-logo.png"
APPROVED_CORPUS_INDEX = PROJECT_ROOT / "data" / "approved_nerc_corpus.sqlite"
LOCAL_DOTENV_PATH = PROJECT_ROOT / ".env"
MODEL_DRAFT_NAME = "moonshotai/Kimi-K3"
APP_DESCRIPTION = (
    "CIP Wayfinder helps utility compliance analysts explore one approved local NERC CIP standard at a time.",
    "It organizes cited source material into draft controls, evidence and baseline observations, potential findings, and remediation steps for human review.",
)
REVIEW_GRAPH_STEPS = (
    "Validate intake scope",
    "Retrieve approved local sources",
    "Create traceable draft controls",
    "Review synthetic evidence and baseline",
    "Create potential findings and remediation",
    "Pause for human approval",
)
LANDING_HIGHLIGHTS = (
    ("1", "Upload", "One authorized public CIP PDF at a time.", "blue", ":material/upload_file:"),
    ("2", "Explore", "Choose the draft analysis that helps your review.", "violet", ":material/search:"),
    ("3", "Decide", "A person reviews, edits, approves, or rejects.", "green", ":material/how_to_reg:"),
)
LANDING_FIELD_HELP = {
    "functional_entity": "Choose a NERC Functional Model role, or type a fictional organization-specific value. This guides the draft; the app does not decide applicability. Do not enter real people or confidential organization data.",
    "jurisdiction": "Choose a NERC Regional Entity context, or type a more specific jurisdiction. This is intake context only and does not decide applicability.",
    "asset_scope": "Choose a safe fictional scope suggestion, or type a synthetic asset group. Do not paste a live IT/OT inventory or operational export.",
    "review_objective": "Choose a draft-review objective, or type a one-sentence objective for the package.",
    "standard_pdf": "Upload one authorized, publicly available PDF named CIP-010-5 or CIP-007-6. The app keeps it in your browser session and reads it locally; do not upload confidential evidence.",
    "authorization": "Check this only when you are allowed to use the document in this local application and it is publicly available.",
}

REFERENCE_OPTIONS = load_nerc_reference_options()


def page_status(settings: AppSettings) -> dict[str, str]:
    """Return display values separately so they can be smoke-tested without Streamlit."""
    return {
        "environment": settings.environment,
        "provider_mode": "local deterministic default; Kimi-K3 is approval-gated" if settings.provider_mode == "fake" else settings.provider_mode,
        "operational_writes": "disabled" if not settings.operational_writes_enabled else "enabled",
    }


def _synthetic_evidence() -> SyntheticEvidenceDocument:
    """Return the safe fixture used when an analyst selects evidence review."""
    return SyntheticEvidenceDocument(document_id="synthetic-ui-evidence-001", label="Synthetic approved change record", document_text="""Evidence ID: synthetic-ui-evidence-001
Asset ID: SUB-ALPHA-RTU-01
Captured On: 2026-08-20
Change Approval: approved
Baseline Fingerprint: baseline-a
""")


def _short_source_excerpt(chunk: RequirementChunk, limit: int = 320) -> str:
    """Return a short local preview while keeping its page/section citation visible."""
    normalized = " ".join(chunk.text.split())
    return normalized if len(normalized) <= limit else f"{normalized[:limit].rstrip()}…"


def _local_chunks_for_uploaded_standard(
    uploaded_standard: UploadedStandard,
    corpus_database_path: Path,
) -> dict[str, list[RequirementChunk]]:
    """Read matching local chunks without creating or modifying the corpus index."""
    try:
        store = LocalCorpusStore(corpus_database_path, read_only=True)
    except (FileNotFoundError, OSError):
        return {}
    return {
        requirement.requirement_reference: store.retrieve(
            RetrievalQuery(
                standard=uploaded_standard.standard,
                requirement_reference=requirement.requirement_reference,
            )
        )
        for requirement in uploaded_standard.requirements
    }


def uploaded_dashboard_data(
    uploaded_standard: UploadedStandard,
    corpus_database_path: Path = APPROVED_CORPUS_INDEX,
) -> dict[str, Any]:
    """Build every draft from matching approved-local chunks when they are available."""
    chunks_by_requirement = _local_chunks_for_uploaded_standard(uploaded_standard, corpus_database_path)
    mappings = []
    for requirement in uploaded_standard.requirements:
        chunks = chunks_by_requirement.get(requirement.requirement_reference, [])
        mappings.append(
            chunk_to_mapping(chunks[0], uploaded_standard.standard.scope_role)
            if chunks
            else analyze_uploaded_standard(uploaded_standard, requirement.requirement_reference).requirement_mapping
        )
    packages: list[dict[str, Any]] = []
    for mapping in mappings:
        generated = generate_draft_control_and_remediation(
            ControlGenerationInput(
                retrieved_mappings=mappings,
                selected_requirement_ids=[mapping.requirement_reference],
            )
        )
        packages.append(
            {
                "mapping": mapping,
                "control": generated.control,
                "remediation": generated.remediation_plan,
                "source_chunks": chunks_by_requirement.get(mapping.requirement_reference, []),
            }
        )
    first_package = packages[0]
    evidence = analyze_evidence(EvidenceAnalysisInput(document=_synthetic_evidence(), expected_asset_id="SUB-ALPHA-RTU-01", expected_baseline_fingerprint="baseline-a", as_of_date=date(2026, 8, 28)))
    data_directory = Path(__file__).resolve().parents[2] / "data" / "synthetic_assets"
    expected = load_expected_snapshots(data_directory / "expected_assets.csv")[0]
    observed = load_observed_snapshots(data_directory / "observed_assets.json")[0]
    baseline = analyze_baseline(expected, observed, first_package["control"].control_id, date(2026, 8, 28))
    return {
        "uploaded": uploaded_standard,
        "mappings": mappings,
        "packages": packages,
        # Retain the first package aliases for existing, beginner-friendly tests.
        "mapping": first_package["mapping"],
        "control": first_package["control"],
        "remediation": first_package["remediation"],
        "evidence": evidence,
        "baseline": baseline,
        "local_source_match_count": sum(bool(chunks) for chunks in chunks_by_requirement.values()),
    }


def _minimal_pdf_bytes() -> bytes:
    """Return a tiny local PDF for pure dashboard contract tests."""
    from io import BytesIO
    from pypdf import PdfWriter

    output = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.write(output)
    return output.getvalue()


def demo_dashboard_data() -> dict[str, Any]:
    """Retain a pure synthetic helper for automated dashboard contract tests."""
    uploaded = validate_uploaded_standard(file_name="CIP-010-5.pdf", file_bytes=_minimal_pdf_bytes(), authorized_public_document=True)
    return uploaded_dashboard_data(uploaded)


def _initialize_session() -> None:
    """Set clear per-browser-session state without persistence or external calls."""
    st.session_state.setdefault("hybrid_messages", [{"role": "assistant", "content": "Welcome. Upload one authorized, publicly available CIP-010-5 or CIP-007-6 PDF to begin a local review."}])
    st.session_state.setdefault("uploaded_standard", None)
    st.session_state.setdefault("workspace", "Start a review")
    st.session_state.setdefault("selected_analysis", None)
    st.session_state.setdefault("last_analysis_choice", None)
    st.session_state.setdefault("case_intake_assessment", None)
    st.session_state.setdefault("model_draft_result", None)
    st.session_state.setdefault("model_draft_summary", None)


def _add_message(role: str, content: str) -> None:
    """Append one safe local chat message without calling a model."""
    st.session_state.hybrid_messages.append({"role": role, "content": content})


def _analysis_response(choice: str) -> str:
    """Return a deterministic explanation of the selected local analysis view."""
    return {
        "Understand the requirement": "I prepared the safe local source details. Review the Source and traceability sections when you are ready.",
        "Create draft controls": "I prepared a traceable draft control. It remains a draft requiring SME tailoring.",
        "Review synthetic evidence and baseline": "I prepared the synthetic evidence and baseline review. It is limited to fictional fixtures and needs SME review.",
        "Review findings and remediation": "I prepared a potential review lead and ordered draft remediation steps. This is not a compliance conclusion.",
    }[choice]


def _render_guided_tour() -> None:
    """Play a brief local-only walkthrough when the learner asks to see the process."""
    with st.status("Showing the four-step local review process", expanded=True) as tour:
        for step in (
            "1. Upload one authorized public CIP standard PDF.",
            "2. Pick the kind of draft analysis you want to see.",
            "3. Review the draft package and its requirement links.",
            "4. A person approves, edits, or rejects; nothing is written automatically.",
        ):
            st.write(step)
            sleep(0.3)
        tour.update(label="Tour complete — you are ready to start", state="complete", expanded=False)


def _render_graph_path_animation() -> None:
    """Animate the documented local graph path without running a write-capable workflow."""
    with st.status("Showing the local graph path", expanded=True) as progress:
        for step_number, step in enumerate(REVIEW_GRAPH_STEPS, start=1):
            st.write(f"{step_number}. {step}")
            sleep(0.2)
        progress.update(label="Graph path reaches the human approval interrupt", state="complete", expanded=False)
    st.caption(compact_graph_summary())


def _render_how_it_works() -> None:
    """Keep the optional visual explanation available without delaying upload."""
    image_path = Path(__file__).resolve().parents[2] / "assets" / "local-review-package-flow.png"
    with st.expander("See the animated review walkthrough", icon=":material/play_circle:"):
        st.write("Upload one approved public standard, choose a question, review the clearly labeled draft package, and make the human decision. Nothing is written automatically.")
        st.image(str(image_path), width="stretch")
        if st.button("Play the 4-step tour", icon=":material/play_arrow:"):
            _render_guided_tour()


def _render_landing_safety_cues() -> None:
    """Keep the landing-page safety boundaries visible without repeating the logo."""
    with st.container(border=True):
        st.subheader("A safe starting point for review", anchor=False)
        st.write("Your uploaded standard stays local to this browser session. The app creates draft guidance for SME tailoring; it does not make a compliance determination or change an operational system.")
        st.badge("Local only", color="blue", icon=":material/laptop_mac:")
        st.badge("Human review required", color="green", icon=":material/person_check:")
        st.badge("Draft guidance", color="violet", icon=":material/edit_note:")


def _render_landing_highlights() -> None:
    """Show three color-coded waypoints without adding more navigation."""
    columns = st.columns(3, vertical_alignment="top")
    for column, (number, title, detail, color, icon) in zip(columns, LANDING_HIGHLIGHTS, strict=True):
        with column.container(border=True):
            st.badge(f"Step {number}", color=color, icon=icon)
            st.write(f"**{title}**")
            st.caption(detail)


def _render_landing_page() -> None:
    """Put the first upload action ahead of optional explanation material."""
    _render_landing_safety_cues()
    st.subheader("Start with one public standard", anchor=False)
    _render_upload_conversation()
    _render_landing_highlights()
    _render_how_it_works()


def _render_upload_conversation() -> None:
    """Render the upload-first step and validate one PDF after user attestation."""
    with st.chat_message("assistant", avatar=":material/upload_file:"):
        st.write("Start with one standard document. The app analyzes it locally in this browser session and does not send it to a model or external service.")
        with st.form("standard_upload_form"):
            st.caption("Tell the Applicability Agent about the review scope. It asks for missing information; it does not guess whether a standard applies.")
            functional_entity = st.selectbox("Functional Entity", REFERENCE_OPTIONS.functional_entities, index=None, key="intake_functional_entity", accept_new_options=True, placeholder="Choose or type a functional entity", help=LANDING_FIELD_HELP["functional_entity"])
            jurisdiction = st.selectbox("Regional Entity / jurisdiction", REFERENCE_OPTIONS.regional_entities, index=None, key="intake_jurisdiction", accept_new_options=True, placeholder="Choose or type a jurisdiction", help=LANDING_FIELD_HELP["jurisdiction"])
            asset_scope = st.selectbox("Asset scope", REFERENCE_OPTIONS.asset_scope_suggestions, index=None, key="intake_asset_scope", accept_new_options=True, placeholder="Choose or type a synthetic asset scope", help=LANDING_FIELD_HELP["asset_scope"])
            review_objective = st.selectbox("Review objective", REFERENCE_OPTIONS.review_objective_suggestions, index=None, key="intake_review_objective", accept_new_options=True, placeholder="Choose or type a review objective", help=LANDING_FIELD_HELP["review_objective"])
            st.caption(f"Functional Entity and Regional Entity choices were collected once from public NERC sources on {REFERENCE_OPTIONS.retrieved_on}. Asset scope and objective are safe local suggestions; type your own when needed.")
            uploaded_file = st.file_uploader("Upload one authorized public standard PDF", type=["pdf"], accept_multiple_files=False, max_upload_size=20, help=LANDING_FIELD_HELP["standard_pdf"])
            attestation = st.checkbox("I confirm this PDF is authorized and publicly available for this local learning review.", help=LANDING_FIELD_HELP["authorization"])
            submitted = st.form_submit_button("Analyze locally", type="primary", icon=":material/verified:")
        if submitted:
            if uploaded_file is None:
                st.error("Choose one PDF before starting local analysis.")
                return
            try:
                uploaded = validate_uploaded_standard(file_name=uploaded_file.name, file_bytes=uploaded_file.getvalue(), authorized_public_document=attestation)
            except UploadValidationError as error:
                st.error(str(error))
                return
            assessment = assess_case_intake(
                CaseIntake(
                    functional_entity=functional_entity,
                    jurisdiction=jurisdiction,
                    asset_scope=asset_scope,
                    review_objective=review_objective,
                ),
                uploaded.standard,
            )
            st.session_state.case_intake_assessment = assessment
            if not assessment.ready_for_review:
                st.warning("The local review has not started because required scope information is missing.", icon=":material/help:")
                for question in assessment.questions:
                    st.write(f"- {question}")
                return
            st.session_state.uploaded_standard = uploaded
            st.session_state.selected_analysis = "Understand the requirement"
            st.session_state.last_analysis_choice = "Understand the requirement"
            _add_message("user", f"Uploaded {uploaded.file_name} for local analysis.")
            _add_message("assistant", "The case scope and PDF were validated locally and are held only in this browser session. Choose what you would like to generate next.")
            st.rerun()


def _render_chat(uploaded_standard: UploadedStandard) -> None:
    """Render a deterministic chat-style task selector after local upload validation."""
    for message in st.session_state.hybrid_messages:
        with st.chat_message(message["role"], avatar=":material/smart_toy:" if message["role"] == "assistant" else None):
            st.write(message["content"])
    st.caption(f"Current local document: {uploaded_standard.file_name} | {uploaded_standard.standard.standard_id}-{uploaded_standard.standard.version} | held in session memory only")
    assessment = st.session_state.case_intake_assessment
    if isinstance(assessment, CaseIntakeAssessment):
        st.caption(f"Case scope: {assessment.intake.functional_entity} | {assessment.intake.jurisdiction} | {assessment.intake.asset_scope}")
    selected = st.pills("Choose an analysis", ANALYSIS_OPTIONS, selection_mode="single", key="analysis_choice")
    if selected and selected != st.session_state.last_analysis_choice:
        _add_message("user", selected)
        _add_message("assistant", _analysis_response(selected))
        st.session_state.selected_analysis = selected
        st.session_state.last_analysis_choice = selected
        st.rerun()
    prompt = st.chat_input("Ask about the selected local analysis", key="local_analysis_chat", max_chars=300)
    if prompt:
        _add_message("user", prompt)
        _add_message("assistant", "This local MVP uses deterministic options rather than a live model. Choose one of the visible analysis options, then open the matching section in Review package.")
        st.rerun()
    if st.button("Clear local session document", icon=":material/delete_sweep:"):
        st.session_state.uploaded_standard = None
        st.session_state.selected_analysis = None
        st.session_state.last_analysis_choice = None
        st.session_state.case_intake_assessment = None
        st.session_state.model_draft_result = None
        st.session_state.model_draft_summary = None
        st.session_state.hybrid_messages = [{"role": "assistant", "content": "The temporary local document view was cleared. Upload one authorized public PDF to begin again."}]
        st.rerun()


def _model_draft_candidate(data: dict[str, Any]) -> dict[str, Any] | None:
    """Choose the first matched requirement for one explicitly approved model call."""
    return next(
        (
            package
            for package in data["packages"]
            if package["source_chunks"] and package["mapping"].requirement_reference.startswith("R")
        ),
        None,
    )


def _render_model_draft_review(data: dict[str, Any]) -> None:
    """Preview and run one human-approved source-grounded drafting request."""
    candidate = _model_draft_candidate(data)
    with st.expander("Review and send a source-grounded draft", icon=":material/send:"):
        st.subheader("Review and send")
        st.caption("This optional step uses the approved Token Factory model only after your explicit approval. It is separate from the local deterministic package.")
        if candidate is None:
            st.warning("No requirement-level match in the approved local corpus is available for a model draft.")
            return
        source = candidate["source_chunks"][0]
        mapping = chunk_to_mapping(source, candidate["mapping"].standard.scope_role)
        generation_input = ControlGenerationInput(
            retrieved_mappings=[mapping],
            selected_requirement_ids=[mapping.requirement_reference],
        )
        request = build_source_grounded_control_draft_request(generation_input)
        st.dataframe(
            [{
                "model": MODEL_DRAFT_NAME,
                "standard/version": f"{mapping.standard.standard_id}-{mapping.standard.version}",
                "requirement": mapping.requirement_reference,
                "source locator": mapping.source_locator,
                "excerpt characters sent": len(mapping.draft_summary),
                "maximum completion tokens": request.max_output_tokens,
                "reasoning effort": request.reasoning_effort,
                "retries": "0 (one attempt)",
            }],
            hide_index=True,
        )
        st.info("The request sends only the displayed requirement's approved public excerpt and citation metadata. It does not send evidence, assets, the uploaded PDF, other requirements, or any operational data.")
        approved = st.checkbox(
            f"I approve sending this one {mapping.standard.standard_id}-{mapping.standard.version} {mapping.requirement_reference} excerpt to Token Factory.",
            key="model_draft_external_approval",
        )
        if st.button("Send approved draft request", type="primary", icon=":material/send:"):
            if not approved:
                st.error("Check the approval statement before sending a model request.")
                return
            provider_environment = load_local_provider_environment(LOCAL_DOTENV_PATH)
            provider_settings = load_provider_settings(provider_environment).model_copy(update={"model": MODEL_DRAFT_NAME})
            if provider_settings.provider != "nebius" or not provider_environment.get("NCI_NEBIUS_API_KEY"):
                st.error("The local Token Factory configuration is not ready. Confirm the provider settings and key in the ignored .env file.")
                return
            try:
                with st.status("Sending the approved source-grounded draft request", expanded=True) as status:
                    result = generate_source_grounded_control_draft(
                        generation_input,
                        build_nebius_provider_from_environment(provider_environment),
                        provider_settings,
                    )
                    status.update(label="Draft received and validated", state="complete", expanded=False)
            except (ProviderResponseError, ProviderTemporaryError, ProviderTimeoutError, ValueError):
                st.error("The model did not return a usable draft. No draft was saved; review the request boundary and try again only if you approve another request.")
                return
            st.session_state.model_draft_result = result.parsed_output
            st.session_state.model_draft_summary = {
                "model": result.model,
                "latency_ms": result.latency_ms,
                "requirement_reference": mapping.requirement_reference,
            }
            st.success("A source-grounded draft was received, traceability-validated, and kept in this browser session only.")
        model_result = st.session_state.get("model_draft_result")
        model_summary = st.session_state.get("model_draft_summary")
        if model_result is not None and isinstance(model_summary, dict):
            st.subheader("Validated model draft")
            st.caption(f"Model: {model_summary['model']} | Latency: {model_summary['latency_ms']} ms | Requirement: {model_summary['requirement_reference']} | Session memory only")
            st.write("**Objective:**", model_result.control.objective.text)
            st.write("**Control type:**", model_result.control.control_type.text)
            st.write("**Owner role:**", model_result.control.owner_role.text)
            st.write("**Procedure:**", model_result.control.procedure.text)
            st.write("**Evidence expectation:**", model_result.control.evidence_expectation.text)
            st.dataframe(
                [{"step": step.step_number, "action": step.action.text, "decision": step.decision.text, "end state": step.end_state.text} for step in model_result.remediation_plan.steps],
                hide_index=True,
            )
            st.caption("Draft only. An SME must tailor and approve this content before any separate export decision.")


def _render_review_package(data: dict[str, Any]) -> None:
    """Show one progressive review package instead of nine peer tabs."""
    uploaded, packages, evidence, baseline = (data["uploaded"], data["packages"], data["evidence"], data["baseline"])
    selected = st.session_state.selected_analysis
    st.subheader("Review package")
    st.caption("Open the sections you need. Source excerpts come from the approved local index; controls, evidence, findings, and remediation remain drafts requiring human review.")
    requirements, matched_sources, controls, status = st.columns(4)
    requirements.metric("Requirement labels", len(packages))
    matched_sources.metric("Local source matches", data["local_source_match_count"])
    controls.metric("Draft controls", len(packages))
    status.metric("Decision status", "Awaiting human review")
    with st.expander("Review graph progress", icon=":material/account_tree:"):
        st.write("This short animation explains the already-tested local graph path. It does not run an export or write a workflow.")
        if st.button("Animate local review path", icon=":material/play_arrow:"):
            _render_graph_path_animation()
    with st.expander("Source and requirement", expanded=selected == "Understand the requirement", icon=":material/article:"):
        st.subheader("Source metadata")
        st.dataframe([{"file": uploaded.file_name, "standard": f"{uploaded.standard.standard_id}-{uploaded.standard.version}", "pages": uploaded.page_count, "stored locally": "No - session memory only"}], hide_index=True)
        st.dataframe([{"requirement reference": item.requirement_reference, "page": item.page} for item in uploaded.requirements], hide_index=True)
        st.caption(f"The package below contains one draft control and remediation plan for all {len(packages)} extracted requirement label(s).")
        for package in packages:
            mapping = package["mapping"]
            source_chunks = package["source_chunks"]
            with st.container(border=True):
                st.markdown(f"#### {mapping.requirement_reference} local source")
                if source_chunks:
                    source = source_chunks[0]
                    st.success("Matched in the approved local source index.", icon=":material/check_circle:")
                    st.dataframe([{
                        "standard/version": f"{source.metadata.standard_id}-{source.metadata.version}",
                        "page": source.metadata.page,
                        "section": source.metadata.section,
                        "source URL": source.metadata.source_url,
                        "retrieval date": str(source.metadata.retrieval_date),
                    }], hide_index=True)
                    st.write("**Short source excerpt:**", _short_source_excerpt(source))
                else:
                    st.warning("No matching approved local source chunk was found for this extracted label. The draft remains metadata-linked only.", icon=":material/warning:")
        st.caption("Source excerpts are for local learning review. An SME must verify each cited source before relying on any draft.")
    with st.expander("Draft controls", expanded=selected == "Create draft controls", icon=":material/fact_check:"):
        st.subheader("Draft controls")
        st.info("Draft only. Organization-specific SME tailoring is required.")
        for package in packages:
            control = package["control"]
            mapping = package["mapping"]
            with st.container(border=True):
                st.markdown(f"#### {mapping.requirement_reference} — page {mapping.source_locator.rsplit(' ', maxsplit=1)[-1]}")
                st.write("**Objective:**", control.objective.text)
                st.write("**Control type:**", control.control_type.text)
                st.write("**Owner role:**", control.owner_role.text)
                st.write("**Performer:**", control.performer.text)
                st.write("**Trigger/frequency:**", control.trigger_frequency.text)
                st.write("**Evidence expectation:**", control.evidence_expectation.text)
                st.write("**Tailoring question:**", control.tailoring_questions[0].text)
    _render_model_draft_review(data)
    with st.expander("Synthetic evidence and baseline", expanded=selected == "Review synthetic evidence and baseline", icon=":material/monitoring:"):
        st.subheader("Synthetic evidence review")
        st.caption("This demonstration uses fictional evidence and asset snapshots. Uploading a standard does not authorize confidential evidence upload.")
        st.dataframe([fact.model_dump() for fact in evidence.observable_facts], hide_index=True)
        st.write("**Possible support:**", evidence.possible_control_support)
        st.write("**Confidence:**", evidence.confidence.value)
        st.write("**SME questions:**", evidence.sme_questions)
        st.subheader("Synthetic baseline comparison")
        st.caption("This view uses simulated asset snapshots only; it does not read a live asset.")
        st.write("**Status:**", baseline.status.value)
        st.write(baseline.summary)
        st.dataframe([exception.model_dump() for exception in baseline.exceptions], hide_index=True)
    with st.expander("Findings and remediation", expanded=selected == "Review findings and remediation", icon=":material/fact_check:"):
        st.subheader("Draft findings")
        st.warning("Potential review lead only. This is not a compliance conclusion and requires human review.")
        st.write("Demo risk rubric: High, Medium, or Low based on synthetic evidence completeness, asset variance, and requirement criticality.")
        st.subheader("Draft remediation workflow")
        for package in packages:
            mapping = package["mapping"]
            remediation = package["remediation"]
            st.markdown(f"#### {mapping.requirement_reference} remediation plan")
            st.dataframe([{"step": step.step_number, "action": step.action.text, "owner": step.owner_role.text, "decision": step.decision.text, "end state": step.end_state.text} for step in remediation.steps], hide_index=True)
        st.info("This is a draft workflow. It cannot create a local export until the existing human approval interrupt is used.")
    with st.expander("Traceability", icon=":material/account_tree:"):
        st.subheader("Traceability")
        traceability_rows = [
            row
            for package in packages
            for row in (
                {"draft item": f"{package['mapping'].requirement_reference} control objective", "retrieved requirement ID": ", ".join(package["control"].objective.requirement_ids)},
                {"draft item": f"{package['mapping'].requirement_reference} remediation step 1", "retrieved requirement ID": ", ".join(package["remediation"].steps[0].action.requirement_ids)},
            )
        ]
        traceability_rows.append({"draft item": f"source file: {uploaded.file_name}", "retrieved requirement ID": ", ".join(mapping.requirement_reference for mapping in data["mappings"])})
        st.dataframe(traceability_rows, hide_index=True)
    with st.expander("Human decision", icon=":material/person_check:"):
        st.subheader("Approve / edit / reject")
        decision = st.segmented_control("Human decision preview", ("approve", "edit", "reject"), key="decision_preview_choice")
        reviewer_role = st.text_input("Reviewer role", key="decision_preview_reviewer_role", max_chars=120)
        decision_notes = st.text_area("Decision rationale", key="decision_preview_notes", max_chars=500, height=90)
        if st.button("Preview selected decision", icon=":material/preview:"):
            if not decision or not reviewer_role.strip() or not decision_notes.strip():
                st.error("Choose a decision and provide both reviewer role and rationale before previewing it.")
            else:
                st.session_state["decision_preview"] = {
                    "decision": decision,
                    "reviewer_role": reviewer_role.strip(),
                    "rationale": decision_notes.strip(),
                }
        if preview := st.session_state.get("decision_preview"):
            st.success(f"In-memory preview: {preview['decision']} by {preview['reviewer_role']}. No case, workflow, or export was written.")
            if preview["decision"] == "edit":
                st.info("The production graph would return this draft to the approval interrupt after the requested edit.", icon=":material/edit:")
            elif preview["decision"] == "reject":
                st.info("The production graph would safely stop with no export.", icon=":material/cancel:")
            else:
                st.info("Approval is only a preview here. The guarded export remains a separate graph action with an explicit interrupt.", icon=":material/lock:")
        st.caption("This screen cannot bypass the LangGraph interrupt or the explicit human approval required before the guarded local export.")


def render_page() -> None:
    """Render the local review app with one optional approval-gated model step."""
    settings = load_settings()
    status = page_status(settings)
    st.set_page_config(page_title=settings.app_name, page_icon=str(APP_LOGO_PATH), layout="wide")
    _initialize_session()
    header_logo, header_text = st.columns((1, 7), vertical_alignment="center")
    with header_logo:
        st.image(str(APP_LOGO_PATH), width=120)
    with header_text:
        st.title(settings.app_name)
        st.write(" ".join(APP_DESCRIPTION))
        st.caption("A local, source-grounded starting point for Low-to-Medium Impact CIP readiness — draft guidance, not a compliance determination.")
    st.info("Upload one authorized public standard PDF. The app reads it locally first. It sends a source excerpt externally only through the separate Review and send approval step; draft controls and fictional evidence/asset examples remain clearly separated from the source document.")
    st.caption(f"Environment: {status['environment']} | Provider: {status['provider_mode']} | Operational writes: {status['operational_writes']}")
    workspace = st.segmented_control(
        "Workspace",
        SCREEN_NAMES,
        default=st.session_state.workspace,
        key="workspace",
        required=True,
        width="stretch",
    )
    uploaded_standard = st.session_state.uploaded_standard
    if workspace == "Start a review":
        if uploaded_standard is None:
            _render_landing_page()
            return
        st.subheader("Start a review")
        _render_chat(uploaded_standard)
        st.info("When you are ready, select **Review package** above to see the organized draft sections.", icon=":material/arrow_forward:")
        return
    if uploaded_standard is None:
        st.info("Upload a standard in **Start a review** before opening the review package.", icon=":material/upload_file:")
        return
    st.caption("This package includes every requirement label extracted from the uploaded standard. Matching approved local source chunks are shown with page/section citations; an SME must verify each source before relying on a draft.")
    _render_review_package(uploaded_dashboard_data(uploaded_standard))
