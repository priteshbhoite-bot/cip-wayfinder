"""Tests for the static, public-source landing-page reference catalog."""

from nerc_compliance_intelligence.reference_options import load_nerc_reference_options


def test_reference_options_are_local_and_have_public_source_provenance() -> None:
    options = load_nerc_reference_options()

    assert options.retrieved_on == "2026-08-31"
    assert "Transmission Operator" in options.functional_entities
    assert "Texas Reliability Entity (Texas RE)" in options.regional_entities
    assert all(source.url.startswith("https://www.nerc.com/") for source in options.sources)


def test_reference_options_contain_only_source_backed_scope_lists() -> None:
    options = load_nerc_reference_options()

    assert not hasattr(options, "asset_scope_suggestions")
