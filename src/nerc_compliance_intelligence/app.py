"""Input-first Streamlit interface for the local, synthetic-data application."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from time import sleep
from typing import Any

import streamlit as st
from nerc_compliance_intelligence.effective_dates import date_summary
from pydantic import ValidationError

from nerc_compliance_intelligence.case_intake import CaseIntake, CaseIntakeAssessment, assess_case_intake
from nerc_compliance_intelligence.cache_policy import CACHE_POLICY_VERSION, DASHBOARD_CACHE_MAX_ENTRIES, CacheMetrics, dashboard_cache_key, file_revision, migrate_cache_metrics, stable_fingerprint
from nerc_compliance_intelligence.config import AppSettings, load_settings
from nerc_compliance_intelligence.control_remediation import ControlGenerationInput, generate_draft_control_and_remediation
from nerc_compliance_intelligence.local_corpus import LocalCorpusStore, RequirementChunk, RetrievalQuery, chunk_to_mapping
from nerc_compliance_intelligence.email_delivery import EmailDeliveryError, WordEmailRequest, load_email_delivery_settings, send_word_package_email, validate_email_address
from nerc_compliance_intelligence.package_export import WORD_MIME_TYPE, ExportDecision, build_review_package_export, render_review_package_docx
from nerc_compliance_intelligence.reference_options import load_nerc_reference_options
from nerc_compliance_intelligence.providers import load_local_provider_environment
from nerc_compliance_intelligence.quality_review import review_source_grounded_package
from nerc_compliance_intelligence.review_package_agent import REVIEW_PACKAGE_OBJECTIVE, ReviewPackageAgentInput, ReviewPackageAgentItem, run_review_package_agent
from nerc_compliance_intelligence.uploaded_standard import UploadValidationError, UploadedRequirementOption, UploadedStandard, analyze_uploaded_standard, validate_uploaded_standard


SCREEN_NAMES = ("Start a review", "Review package")
PROJECT_ROOT = Path(__file__).resolve().parents[2]
APP_LOGO_PATH = PROJECT_ROOT / "assets" / "cip-wayfinder-logo.png"
APPROVED_CORPUS_INDEX = PROJECT_ROOT / "data" / "approved_nerc_corpus.sqlite"
APPROVED_CORPUS_DIRECTORY = PROJECT_ROOT.parent / "approved-nerc-corpus"
APPROVED_CORPUS_MANIFEST = PROJECT_ROOT / "data" / "corpus_manifests" / "approved_cip_manifest.json"
LOCAL_DOTENV_PATH = PROJECT_ROOT / ".env"
APP_DESCRIPTION = (
    "CIP Wayfinder helps utility compliance analysts explore one authorized NERC standards-related PDF at a time.",
    "It builds a local document profile and organizes source-grounded knowledge into draft controls and remediation steps for human review.",
)
REVIEW_GRAPH_STEPS = (
    "Validate intake scope",
    "Retrieve approved local sources",
    "Assemble a source-grounded draft package",
    "Pause for human approval",
)
LANDING_HIGHLIGHTS = (
    ("1", "Upload", "One authorized public CIP PDF at a time.", "blue", ":material/upload_file:"),
    ("2", "Explore", "Choose the draft analysis that helps your review.", "violet", ":material/search:"),
    ("3", "Decide", "A person reviews, edits, approves, or rejects.", "green", ":material/how_to_reg:"),
)
LANDING_FIELD_HELP = {
    "functional_entity": "Choose every NERC Functional Model role relevant to this review, or type a fictional organization-specific value. This guides the draft; the app does not decide applicability. Do not enter real people or confidential organization data.",
    "jurisdiction": "Choose every NERC Regional Entity context relevant to this review, or type a more specific jurisdiction. This is intake context only and does not decide applicability.",
    "standard_pdf": "Upload one authorized, publicly available, searchable PDF published or shared by NERC and tied to a recognized Reliability Standard. The app reads its content locally to verify the NERC relationship; do not upload confidential evidence.",
    "authorization": "Check this only when you are allowed to use the document in this local application and it is publicly available.",
}

REFERENCE_OPTIONS = load_nerc_reference_options()


def page_status(settings: AppSettings) -> dict[str, str]:
    """Return display values separately so they can be smoke-tested without Streamlit."""
    return {
        "environment": settings.environment,
        "provider_mode": "local deterministic workflow" if settings.provider_mode == "fake" else settings.provider_mode,
        "operational_writes": "disabled" if not settings.operational_writes_enabled else "enabled",
    }


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
                standard=(requirement.standard or uploaded_standard.standard).model_dump(),
                requirement_reference=(
                    requirement.source_requirement_reference
                    or requirement.requirement_reference
                ),
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
        if chunks:
            source_scope = requirement.standard or uploaded_standard.standard
            first_mapping = chunk_to_mapping(chunks[0], source_scope.scope_role)
            mappings.append(
                first_mapping.model_copy(
                    update={
                        "requirement_reference": requirement.requirement_reference,
                        "draft_summary": "\n\n".join(chunk.text for chunk in chunks),
                    }
                )
            )
        else:
            mappings.append(analyze_uploaded_standard(uploaded_standard, requirement.requirement_reference).requirement_mapping)
    package_items: list[ReviewPackageAgentItem] = []
    for mapping, knowledge_item in zip(mappings, uploaded_standard.requirements, strict=True):
        generated = generate_draft_control_and_remediation(
            ControlGenerationInput(
                retrieved_mappings=mappings,
                selected_requirement_ids=[mapping.requirement_reference],
            )
        )
        package_items.append(
            ReviewPackageAgentItem(
                mapping=mapping,
                control=generated.control,
                remediation=generated.remediation_plan,
                source_chunks=chunks_by_requirement.get(mapping.requirement_reference, []),
                knowledge_item=knowledge_item,
            )
        )
    agent_output = run_review_package_agent(
        ReviewPackageAgentInput(
            uploaded_standard=uploaded_standard,
            items=package_items,
        )
    )
    quality_review = review_source_grounded_package(agent_output)
    packages = [
        {
            "mapping": item.mapping,
            "control": item.control,
            "remediation": item.remediation,
            "source_chunks": item.source_chunks,
            "knowledge_item": item.knowledge_item,
        }
        for item in agent_output.items
    ]
    first_package = packages[0]
    return {
        "uploaded": uploaded_standard,
        "review_package_agent": agent_output,
        "quality_review": quality_review,
        "mappings": mappings,
        "packages": packages,
        # Retain the first package aliases for existing, beginner-friendly tests.
        "mapping": first_package["mapping"],
        "control": first_package["control"],
        "remediation": first_package["remediation"],
        "local_source_match_count": agent_output.local_source_match_count,
    }


@st.cache_data(max_entries=DASHBOARD_CACHE_MAX_ENTRIES, show_spinner=False)
def _cached_uploaded_dashboard_data(
    uploaded_standard_json: str,
    corpus_database_path: str,
    corpus_revision: str,
    cache_policy_version: str,
) -> dict[str, Any]:
    """Cache public-source-derived package data with explicit invalidation inputs."""
    del corpus_revision, cache_policy_version
    return uploaded_dashboard_data(
        UploadedStandard.model_validate_json(uploaded_standard_json),
        Path(corpus_database_path),
    )


def cached_uploaded_dashboard_data(
    uploaded_standard: UploadedStandard,
    corpus_database_path: Path = APPROVED_CORPUS_INDEX,
) -> dict[str, Any]:
    """Use the shared data cache and count reuse visible to this browser session."""
    cache_key = dashboard_cache_key(uploaded_standard, corpus_database_path)
    seen_keys = st.session_state.setdefault("seen_dashboard_cache_keys", set())
    metrics = migrate_cache_metrics(st.session_state.get("cache_metrics"))
    if cache_key in seen_keys:
        metrics.dashboard_hits += 1
    else:
        metrics.dashboard_misses += 1
        seen_keys.add(cache_key)
    st.session_state.cache_metrics = metrics.model_dump()
    return _cached_uploaded_dashboard_data(
        uploaded_standard.model_dump_json(),
        str(corpus_database_path),
        file_revision(corpus_database_path),
        CACHE_POLICY_VERSION,
    )


def demo_dashboard_data() -> dict[str, Any]:
    """Retain a pure synthetic helper for automated dashboard contract tests."""
    uploaded = UploadedStandard(
        file_name="CIP-010-5.pdf",
        content_hash="0" * 64,
        standard={"standard_id": "CIP-010", "version": "5", "scope_role": "primary"},
        page_count=1,
        extracted_character_count=180,
        requirements=[
            UploadedRequirementOption(
                requirement_reference="Document overview",
                page=1,
                title="Synthetic NERC document overview",
                summary="Synthetic local NERC standards material for deterministic dashboard tests.",
            )
        ],
        document_title="Synthetic CIP-010-5 learning document",
        document_type="NERC Reliability Standard",
        referenced_standards=[
            {"standard_id": "CIP-010", "version": "5", "scope_role": "primary"}
        ],
        nerc_identity_signals=["synthetic test fixture"],
    )
    return uploaded_dashboard_data(uploaded)


def _initialize_session() -> None:
    """Set clear per-browser-session state without persistence or external calls."""
    if st.session_state.get("document_knowledge_version") != CACHE_POLICY_VERSION:
        for stale_key in (
            "uploaded_standard",
            "selected_analysis",
            "last_analysis_choice",
            "case_intake_assessment",
            "decision_preview",
            "approved_package_bytes",
            "approved_package_file_name",
            "approved_package_context_key",
            "email_delivery_receipt",
            "seen_dashboard_cache_keys",
        ):
            st.session_state.pop(stale_key, None)
        st.session_state.document_knowledge_version = CACHE_POLICY_VERSION
    st.session_state.setdefault("hybrid_messages", [{"role": "assistant", "content": "Welcome. Upload one authorized, publicly available NERC standards-related PDF to begin a local review."}])
    st.session_state.setdefault("uploaded_standard", None)
    st.session_state.setdefault("workspace", "Start a review")
    st.session_state.setdefault("selected_analysis", None)
    st.session_state.setdefault("last_analysis_choice", None)
    st.session_state.setdefault("case_intake_assessment", None)
    st.session_state.setdefault("seen_dashboard_cache_keys", set())
    st.session_state.cache_metrics = migrate_cache_metrics(st.session_state.get("cache_metrics")).model_dump()
    st.session_state.setdefault("decision_preview", None)
    st.session_state.setdefault("approved_package_bytes", None)
    st.session_state.setdefault("approved_package_file_name", None)
    st.session_state.setdefault("approved_package_context_key", None)
    st.session_state.setdefault("email_delivery_receipt", None)
    prior_decision = st.session_state.get("decision_preview")
    if isinstance(prior_decision, dict) and prior_decision.get("decision") == "Approve for email delivery":
        prior_decision["decision"] = "Approve package"
    if st.session_state.get("package_export_decision_choice") == "Approve for email delivery":
        st.session_state.package_export_decision_choice = "Approve package"
    if isinstance(prior_decision, dict) and prior_decision.get("decision") not in {"Approve package", "Needs editing", "Reject"}:
        st.session_state.decision_preview = None


def _add_message(role: str, content: str) -> None:
    """Append one safe local chat message without calling a model."""
    st.session_state.hybrid_messages.append({"role": role, "content": content})


def _render_guided_tour() -> None:
    """Show the simplified local-review flow without running the graph."""
    with st.status("Walking through the local review", expanded=True) as status:
        for step_number, step in enumerate(REVIEW_GRAPH_STEPS, start=1):
            st.write(f"{step_number}. {step}")
            sleep(0.15)
        status.update(label="Walkthrough complete", state="complete", expanded=False)


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
    """Show the single necessary first action, with optional process detail."""
    st.subheader("Start a review", anchor=False)
    st.caption("Upload one authorized public NERC standards-related PDF and define the local review scope. Results are drafts for human review.")
    _render_upload_conversation()
    _render_how_it_works()


def _render_upload_conversation() -> None:
    """Render the upload-first step and validate one PDF after user attestation."""
    with st.chat_message("assistant", avatar=":material/upload_file:"):
        st.write("Start with one searchable NERC standards-related PDF. The app verifies and analyzes it locally in this browser session and does not send it to a model or external service.")
        st.info(
            f"**What CIP Wayfinder will produce:** {REVIEW_PACKAGE_OBJECTIVE} "
            "The package includes document insights, citations, draft controls, and remediation guidance.",
            icon=":material/inventory_2:",
        )
        with st.form("standard_upload_form"):
            st.caption("Tell the Applicability Agent about the review scope. It asks for missing information; it does not guess whether a standard applies.")
            functional_entity = st.multiselect("Functional Entity", REFERENCE_OPTIONS.functional_entities, key="intake_functional_entity", accept_new_options=True, placeholder="Choose or type all relevant roles", help=LANDING_FIELD_HELP["functional_entity"])
            jurisdiction = st.multiselect("Regional Entity", REFERENCE_OPTIONS.regional_entities, key="intake_jurisdiction", accept_new_options=True, placeholder="Choose or type all relevant regions", help=LANDING_FIELD_HELP["jurisdiction"])
            st.caption(f"Functional Entity and Regional Entity choices were collected once from public NERC sources on {REFERENCE_OPTIONS.retrieved_on}. You may type an organization-specific role or region when needed.")
            uploaded_file = st.file_uploader("Upload one authorized public NERC standards-related PDF", type=["pdf"], accept_multiple_files=False, max_upload_size=20, help=LANDING_FIELD_HELP["standard_pdf"])
            attestation = st.checkbox("I confirm this PDF is authorized and publicly available for this local learning review.", help=LANDING_FIELD_HELP["authorization"])
            submit_column, feedback_column = st.columns(
                [1, 4],
                gap="small",
                vertical_alignment="center",
            )
            with submit_column:
                submitted = st.form_submit_button("Analyze locally", type="primary", icon=":material/verified:")
            with feedback_column:
                upload_feedback = st.empty()
        if submitted:
            if uploaded_file is None:
                upload_feedback.error("Choose one PDF before starting local analysis.")
                return
            try:
                uploaded = validate_uploaded_standard(
                    file_name=uploaded_file.name,
                    file_bytes=uploaded_file.getvalue(),
                    authorized_public_document=attestation,
                    approved_corpus_directory=APPROVED_CORPUS_DIRECTORY,
                    approved_corpus_manifest_path=APPROVED_CORPUS_MANIFEST,
                )
            except UploadValidationError as error:
                upload_feedback.error(str(error))
                return
            try:
                assessment = assess_case_intake(
                    CaseIntake(
                        functional_entity=functional_entity,
                        jurisdiction=jurisdiction,
                    ),
                    uploaded.standard,
                )
            except ValidationError:
                st.error("Check the review scope values and try again. You may select all relevant Functional Entities and Regional Entities.")
                return
            st.session_state.case_intake_assessment = assessment
            if not assessment.ready_for_review:
                st.warning("The local review has not started because required scope information is missing.", icon=":material/help:")
                for question in assessment.questions:
                    st.write(f"- {question}")
                return
            st.session_state.uploaded_standard = uploaded
            st.session_state.selected_analysis = "Understand the requirement"
            st.session_state.last_analysis_choice = "Understand the requirement"
            st.session_state.decision_preview = None
            st.session_state.approved_package_bytes = None
            st.session_state.approved_package_file_name = None
            st.session_state.approved_package_context_key = None
            st.session_state.email_delivery_receipt = None
            _add_message("user", f"Uploaded {uploaded.file_name} for local analysis.")
            _add_message("assistant", "The case scope and PDF were validated locally and are held only in this browser session. Choose what you would like to generate next.")
            st.rerun()


def _open_review_workspace() -> None:
    """Switch workspaces before the keyed selector is rendered on the rerun."""
    st.session_state.workspace = "Review package"


def _render_chat(uploaded_standard: UploadedStandard) -> None:
    """Show a concise handoff from upload to the review package."""
    assessment = st.session_state.case_intake_assessment
    st.subheader("Review ready", anchor=False)
    st.success("Your standard and review scope were validated locally. No information was sent to an external model.", icon=":material/check_circle:")
    st.caption(
        f"Document: {uploaded_standard.file_name} | "
        f"{uploaded_standard.document_type} | "
        f"primary reference {uploaded_standard.standard.standard_id}-{uploaded_standard.standard.version} | session only"
    )
    st.caption(
        f"Local knowledge profile: {len(uploaded_standard.requirements)} items across "
        f"{len(uploaded_standard.referenced_standards) or 1} referenced standard versions"
    )
    if isinstance(assessment, CaseIntakeAssessment):
        st.caption(
            "Scope: "
            f"{', '.join(assessment.intake.functional_entity)} | "
            f"{', '.join(assessment.intake.jurisdiction)}"
        )
    st.button(
        "Open review package",
        type="primary",
        icon=":material/folder_open:",
        on_click=_open_review_workspace,
    )
    if st.button("Clear local session document", icon=":material/delete_sweep:"):
        st.session_state.uploaded_standard = None
        st.session_state.selected_analysis = None
        st.session_state.last_analysis_choice = None
        st.session_state.case_intake_assessment = None
        st.session_state.seen_dashboard_cache_keys = set()
        st.session_state.cache_metrics = CacheMetrics().model_dump()
        st.session_state.decision_preview = None
        st.session_state.approved_package_bytes = None
        st.session_state.approved_package_file_name = None
        st.session_state.approved_package_context_key = None
        st.session_state.email_delivery_receipt = None
        st.session_state.hybrid_messages = [{"role": "assistant", "content": "The temporary local document view was cleared. Upload one authorized public PDF to begin again."}]
        st.rerun()


def _package_context_key(data: dict[str, Any]) -> str:
    """Bind approval to the exact local package and intake."""
    assessment = st.session_state.get("case_intake_assessment")
    return stable_fingerprint(
        "word-email-context",
        {
            "dashboard_key": dashboard_cache_key(data["uploaded"], APPROVED_CORPUS_INDEX),
            "assessment": assessment.model_dump(mode="json") if isinstance(assessment, CaseIntakeAssessment) else None,
        },
    )


def _prepare_approved_word_package(
    data: dict[str, Any],
    reviewer_role: str,
    rationale: str,
) -> None:
    """Create one in-memory Word attachment only after package approval."""
    assessment = st.session_state.get("case_intake_assessment")
    decision = ExportDecision(
        reviewer_role=reviewer_role,
        rationale=rationale,
        recorded_at=datetime.now(timezone.utc),
    )
    package = build_review_package_export(
        data,
        assessment if isinstance(assessment, CaseIntakeAssessment) else None,
        decision,
    )
    st.session_state.approved_package_bytes = render_review_package_docx(package)
    safe_standard = package.standard_version.lower().replace("-", "_")
    st.session_state.approved_package_file_name = f"cip_wayfinder_{safe_standard}_draft_review.docx"
    st.session_state.approved_package_context_key = _package_context_key(data)
    st.session_state.email_delivery_receipt = None


def _requirement_vital_summary(knowledge_item: UploadedRequirementOption) -> str:
    """Show a source-derived synopsis rather than reusing a generated control."""
    return f"**What it requires:** {knowledge_item.summary}"


def _official_requirement_text(
    source_chunks: list[RequirementChunk],
    knowledge_item: UploadedRequirementOption,
) -> str | None:
    """Prefer approved-corpus wording, then the bounded uploaded source block."""
    if source_chunks:
        return "\n\n".join(source.text.strip() for source in source_chunks if source.text.strip()) or None
    return knowledge_item.source_text.strip() if knowledge_item.source_text else None


def _requirement_source_line(source_chunks: list[RequirementChunk]) -> str:
    """Return one compact traceability line for all displayed source chunks."""
    locations = [
        (
            f"pages {source.metadata.page}-{source.metadata.end_page}, {source.metadata.section}"
            if source.metadata.end_page and source.metadata.end_page != source.metadata.page
            else f"page {source.metadata.page}, {source.metadata.section}"
        )
        for source in source_chunks
    ]
    unique_locations = list(dict.fromkeys(locations))
    retrieval_dates = list(dict.fromkeys(str(source.metadata.retrieval_date) for source in source_chunks))
    return f"Source: {'; '.join(unique_locations)} | retrieved {', '.join(retrieval_dates)}"


def _render_review_package(data: dict[str, Any]) -> None:
    """Show the essential review content in three progressive sections."""
    uploaded, packages = data["uploaded"], data["packages"]
    st.subheader("Review package")
    agent_output = data["review_package_agent"]
    st.caption(f"Review Package Agent objective: {agent_output.objective}")
    quality_review = data["quality_review"]
    if quality_review.is_valid:
        st.caption("Quality Reviewer: structural traceability checks passed; warnings still require SME attention.")
    st.caption("Read cited sources, inspect draft guidance, then make a human decision.")
    requirements, effective_date, controls = st.columns(3)
    requirements.metric("Knowledge items", len(packages))
    date_info = uploaded.effective_date_info
    schedule = uploaded.effective_date_schedule
    schedule_summary = date_summary(schedule) if schedule else None
    summary_label = {
        "Multiple effective dates": "Multiple dates",
        "Incomplete dates": "Incomplete",
        "Review date notes": "Review notes",
    }.get(schedule_summary, schedule_summary)
    effective_date.metric(
        "Standard effective date",
        summary_label if schedule else (date_info.date.isoformat() if date_info else "Not verified"),
        help="For the exact uploaded standard/version, as reported by the supplied jurisdiction-specific reference. This is not a live regulatory check. Publication, approval, and retrieval dates are not substituted.",
    )
    if schedule:
        source_pages = ", ".join(str(page) for page in sorted({row.page for row in schedule.rows}))
        effective_date.text(
            f"Source: {schedule.source_name} — page(s) {source_pages}",
            width="stretch",
        )
        effective_date.caption(f"{schedule.jurisdiction} · supplied reference snapshot")
        if summary_label != schedule_summary:
            effective_date.caption(schedule_summary)
    elif date_info:
        effective_date.text(f"Jurisdiction: {date_info.jurisdiction}\nSource: {date_info.source_reference}")
    controls.metric("Draft controls", len(packages))
    referenced_labels = ", ".join(
        f"{item.standard_id}-{item.version}" for item in uploaded.referenced_standards
    ) or f"{uploaded.standard.standard_id}-{uploaded.standard.version}"
    st.caption(
        f"Detected document: {uploaded.document_title} | {uploaded.document_type} | "
        f"Referenced standards: {referenced_labels}"
    )
    if uploaded.document_type != "NERC Reliability Standard":
        st.info(
            "This file was identified as NERC standards-related supporting material, not as a Reliability Standard. "
            "Its knowledge and control outputs remain non-binding drafts for SME review.",
            icon=":material/info:",
        )

    with st.expander("Requirements and sources", expanded=False, icon=":material/article:"):
        st.caption(
            f"{uploaded.file_name} | {uploaded.document_type} | "
            "content-validated and read locally; held in this browser session only"
        )
        st.markdown(
            f"**Primary standard:** {uploaded.standard.standard_id}-{uploaded.standard.version}"
        )
        if agent_output.missing_information:
            st.warning(
                f"The Review Package Agent flagged {len(agent_output.missing_information)} item(s) "
                "without an approved local corpus match. Verify their uploaded-document summaries "
                "against the official NERC source before relying on the drafts.",
                icon=":material/find_in_page:",
            )
        for package in packages:
            mapping = package["mapping"]
            source_chunks = package["source_chunks"]
            knowledge_item = package["knowledge_item"]
            with st.container(border=True, gap="small"):
                requirement_label = (
                    f"{mapping.requirement_reference} — {knowledge_item.domain}"
                    if knowledge_item.domain != "Requirement"
                    else mapping.requirement_reference
                )
                show_requirement = st.toggle(
                    requirement_label,
                    value=False,
                    key=f"requirement_source_{mapping.requirement_reference}",
                )
                if show_requirement:
                    if schedule:
                        dated_rows = [row for row in schedule.rows if not row.no_parts and (
                            row.requirement == mapping.requirement_reference or row.requirement.startswith(mapping.requirement_reference + ".")
                        )]
                        for row in dated_rows:
                            st.text(f"{row.requirement} effective date (U.S.): {row.part_date or row.requirement_date or 'Not specified'} | {row.status} | Source note: {row.source_note or 'None'} | {schedule.source_name}, page {row.page}, row {row.row_id}")
                        if not dated_rows:
                            st.caption("Effective date: no matching requirement row in the supplied reference.")
                    domain_column, source_column = st.columns([2, 3])
                    with domain_column:
                        st.markdown("**Domain**")
                        st.text(knowledge_item.domain)
                    with source_column:
                        st.markdown("**Source location**")
                        if source_chunks:
                            st.text(_requirement_source_line(source_chunks))
                        else:
                            st.text(mapping.source_locator)
                    st.markdown("**What the requirement means**")
                    st.caption("Plain-language summary; verify it against the official text below.")
                    st.text(knowledge_item.summary)
                    st.markdown("**Applicable systems**")
                    st.text(knowledge_item.applicable_systems)
                    official_requirement = _official_requirement_text(source_chunks, knowledge_item)
                    if official_requirement:
                        st.markdown("**Official requirement text**")
                        st.text(official_requirement, width="stretch")
                        st.caption(
                            "Extracted from the locally read PDF. Text wraps to fit the available width."
                        )
        st.caption("Use each citation to verify the official NERC requirement before relying on any draft guidance.")

    with st.expander("Draft controls and remediation", expanded=False, icon=":material/fact_check:"):
        st.caption("All content below is a draft starting point. Organization-specific SME tailoring is required.")
        for package in packages:
            control = package["control"]
            mapping = package["mapping"]
            remediation = package["remediation"]
            knowledge_item = package["knowledge_item"]
            with st.container(border=True, gap="small"):
                show_control = st.toggle(
                    f"{mapping.requirement_reference} — {control.title.text}",
                    value=False,
                    key=f"control_remediation_{mapping.requirement_reference}",
                )
                if show_control:
                    identity_column, domain_column = st.columns([2, 3])
                    with identity_column:
                        st.markdown("**Draft control ID**")
                        st.text(control.control_id, width="stretch")
                    with domain_column:
                        st.markdown("**Control domain**")
                        st.text(knowledge_item.domain)
                    st.markdown("**Applicable systems**")
                    st.text(knowledge_item.applicable_systems)
                    st.markdown("**Control objective**")
                    st.text(control.objective.text)
                    st.markdown("**Required control activities**")
                    for activity in control.activities:
                        st.write(f"- {activity.activity.text}")
                    owner_column, frequency_column = st.columns(2)
                    with owner_column:
                        st.markdown("**Owner and performer**")
                        st.text(f"{control.owner_role.text}\n{control.performer.text}")
                    with frequency_column:
                        st.markdown("**Frequency or trigger**")
                        st.text(control.trigger_frequency.text)
                    st.markdown("**Implementation procedure**")
                    st.text(control.procedure.text)
                    st.markdown("**Evidence expected**")
                    st.text(control.evidence_expectation.text)
                    st.markdown("**Control test**")
                    st.text(control.test_procedure.text)
                    st.markdown("**Potential condition to assess**")
                    st.text(
                        "A remediation item may be needed when the organization cannot demonstrate "
                        f"the documented process, implementation, or evidence for {mapping.requirement_reference}."
                    )
                    st.markdown("**Draft remediation workflow**")
                    remediation_stages = (
                        "Immediate containment",
                        "Corrective action",
                        "Validation and closure",
                    )
                    for step in remediation.steps:
                        st.markdown(f"**Step {step.step_number}: {remediation_stages[step.step_number - 1]}**")
                        for label, value in (
                            ("Action", step.action.text),
                            ("Owner", step.owner_role.text),
                            ("Decision", step.decision.text),
                            ("End state", step.end_state.text),
                        ):
                            st.markdown(f"**{label}**")
                            st.text(value, width="stretch")
                    st.markdown("**SME tailoring question**")
                    st.text(control.tailoring_questions[0].text)
                    st.caption(
                        f"Every draft statement remains traceable to {mapping.requirement_reference}. "
                        "No gap, control, or remediation is approved automatically."
                    )
        st.warning("Potential gaps and remediation steps are review observations, not compliance conclusions or automatic closures.", icon=":material/person_check:")

    with st.expander("Human decision", expanded=False, icon=":material/person_check:"):
        st.write("Make a decision on the draft package you can see above. Approval prepares a Word attachment; it does not send email, declare compliance, or implement a control.")
        st.info("Word formatting is created locally from the reviewed package and does not require a model call.")
        with st.form("package_export_decision_form"):
            decision_label = st.segmented_control(
                "Package decision",
                ("Approve package", "Needs editing", "Reject"),
                key="package_export_decision_choice",
            )
            reviewer_role = st.text_input("Reviewer role", key="decision_preview_reviewer_role", max_chars=120)
            decision_notes = st.text_area("Decision rationale", key="decision_preview_notes", max_chars=500, height=90)
            submitted = st.form_submit_button("Apply package decision", type="primary", icon=":material/task_alt:")
        if submitted:
            allowed_decisions = {"Approve package", "Needs editing", "Reject"}
            if decision_label not in allowed_decisions or not reviewer_role.strip() or not decision_notes.strip():
                st.error("Choose a valid decision and provide both reviewer role and rationale.")
            elif decision_label == "Approve package" and not quality_review.is_valid:
                st.error("The package failed structural quality checks and cannot be approved.")
            else:
                st.session_state.decision_preview = {
                    "decision": decision_label,
                    "reviewer_role": reviewer_role.strip(),
                    "rationale": decision_notes.strip(),
                }
                st.session_state.approved_package_bytes = None
                st.session_state.approved_package_file_name = None
                st.session_state.approved_package_context_key = None
                st.session_state.email_delivery_receipt = None
                if decision_label == "Approve package":
                    _prepare_approved_word_package(data, reviewer_role.strip(), decision_notes.strip())
                st.rerun()

        preview = st.session_state.get("decision_preview")
        if isinstance(preview, dict):
            if preview.get("decision") == "Approve package":
                st.success(f"Package approved by {preview['reviewer_role']}. It is ready to download or email; this is not a compliance approval.")
            elif preview.get("decision") == "Needs editing":
                st.warning("The package was returned for editing. No attachment was created or sent.")
            else:
                st.error("The draft package was rejected. No attachment was created or sent.")

        package_bytes = st.session_state.get("approved_package_bytes")
        package_name = st.session_state.get("approved_package_file_name")
        package_context = st.session_state.get("approved_package_context_key")
        if isinstance(package_bytes, bytes) and isinstance(package_name, str):
            if package_context != _package_context_key(data):
                st.warning("The review content changed after approval. Apply a new package decision before downloading or emailing it.")
            else:
                st.subheader("Download approved Word package", anchor=False)
                st.caption("Download the approved draft directly to your device. This does not send an email or write to an operational system.")
                st.download_button(
                    "Download approved Word package",
                    data=package_bytes,
                    file_name=package_name,
                    mime=WORD_MIME_TYPE,
                    type="primary",
                    icon=":material/download:",
                )
                st.subheader("Email approved Word package", anchor=False)
                st.caption("This is a separate external action. Review the destination and attachment, then explicitly approve the send.")
                with st.form("approved_package_email_form"):
                    recipient = st.text_input(
                        "Recipient email address",
                        key="approved_package_recipient",
                        placeholder="reviewer@example.com",
                        max_chars=254,
                    )
                    st.write(f"**Attachment:** {package_name} ({len(package_bytes) / 1024:.1f} KB)")
                    st.write(f"**Standard:** {uploaded.standard.standard_id}-{uploaded.standard.version}")
                    send_approved = st.checkbox(
                        "I approve sending this draft Word package to the email address above using the configured SMTP service.",
                        key="approved_package_send_authorization",
                    )
                    send_submitted = st.form_submit_button(
                        "Send approved Word package",
                        type="primary",
                        icon=":material/send:",
                    )
                if send_submitted:
                    try:
                        validated_recipient = validate_email_address(recipient)
                    except ValueError as error:
                        st.error(str(error))
                    else:
                        if not send_approved:
                            st.error("Confirm the email-send authorization before sending.")
                        elif package_context != _package_context_key(data):
                            st.error("The package changed. Review it and approve it again before sending.")
                        else:
                            try:
                                email_environment = load_local_provider_environment(LOCAL_DOTENV_PATH)
                                email_settings = load_email_delivery_settings(email_environment)
                                request = WordEmailRequest(
                                    recipient=validated_recipient,
                                    subject=f"CIP Wayfinder draft review package — {uploaded.standard.standard_id}-{uploaded.standard.version}",
                                    body=(
                                        "Attached is the approved CIP Wayfinder draft review package. "
                                        "It is draft guidance for authorized SME review and is not a compliance determination or legal advice."
                                    ),
                                    attachment_name=package_name,
                                    attachment_bytes=package_bytes,
                                )
                                receipt = send_word_package_email(request, email_settings)
                            except EmailDeliveryError as error:
                                st.error(str(error))
                            except ValidationError:
                                st.error("The email request could not be prepared. Review the recipient and approved package, then try again.")
                            else:
                                st.session_state.email_delivery_receipt = receipt.model_dump(mode="json")
                                st.rerun()
                receipt = st.session_state.get("email_delivery_receipt")
                if isinstance(receipt, dict):
                    st.success(
                        f"Sent {receipt['attachment_name']} to {receipt['masked_recipient']} at {receipt['sent_at']}."
                    )
                    st.caption("Only this masked delivery receipt is kept in browser session memory.")

def render_page() -> None:
    """Render the local review app with approval-gated package delivery."""
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
    _render_review_package(cached_uploaded_dashboard_data(uploaded_standard))
