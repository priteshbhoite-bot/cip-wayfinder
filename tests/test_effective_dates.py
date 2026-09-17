"""Synthetic tests for date-column selection and safe standard-level summaries."""

from datetime import date

import pytest
from pydantic import ValidationError

from nerc_compliance_intelligence.effective_dates import EffectiveDateSchedule, RequirementDate, date_summary, parse_date_table
from nerc_compliance_intelligence.source_catalog import CATALOG_PATH, CatalogDocument, SourceCatalog
from streamlit.testing.v1 import AppTest


def schedule(rows: list[RequirementDate]) -> EffectiveDateSchedule:
    return EffectiveDateSchedule(standard_version="CIP-015-2", source_name="Synthetic dates.pdf",
        source_sha256="a" * 64, extracted_on=date(2026, 9, 17), rows=rows)


def row(number: int = 1, **changes: object) -> RequirementDate:
    values = dict(row_id=number, requirement=f"R{number}", requirement_date="2029-10-01",
        part_date=None, inactive_date=None, status="Synthetic future status", page=95)
    return RequirementDate.model_validate({**values, **changes})


def test_shared_requirement_date_summary() -> None:
    assert date_summary(schedule([row(), row(2)])) == "2029-10-01"


def test_packaged_reference_matches_all_catalog_versions_and_preserves_page_95() -> None:
    catalog = SourceCatalog.model_validate_json(CATALOG_PATH.read_bytes())
    for item in catalog.documents:
        assert item.effective_date_schedule is not None
        assert item.effective_date_schedule.standard_version == f"{item.standard_id}-{item.version}"
    cip015 = next(item for item in catalog.documents if item.standard_id == "CIP-015" and item.version == "2")
    record = cip015.effective_date_schedule
    assert date_summary(record) == "2029-10-01"
    assert {row.page for row in record.rows} == {95}
    assert {row.row_id for row in record.rows} == set(range(589, 597))


def test_phased_part_dates_are_not_replaced_by_requirement_date() -> None:
    assert date_summary(schedule([row(), row(2, requirement="R1.1", part_date="2030-01-01")])) == "Multiple effective dates"


def test_missing_dates_and_annotated_rows_do_not_produce_single_date() -> None:
    assert date_summary(schedule([row(requirement_date=None)])) == "Not specified"
    assert date_summary(schedule([row(), row(2, requirement_date=None)])) == "Incomplete dates"
    assert date_summary(schedule([row(source_note="DO NOT USE")])) == "Review date notes"


def test_regulatory_order_date_is_not_effective_date() -> None:
    header = ["#", "Status", "Standard", "Standard Version", "Requirement / Part",
              "Regulatory Order Effective Date", "Effective Date of Requirement",
              "Effective Date of Part", "Inactive Date of Requirement / Part"]
    data = ["1", "Subject to Future\nEnforcement", "CIP-015", "CIP-015-2", "1.1.",
            "Aug 10, 2026", "Oct 1, 2029", "Jan 1, 2030", ""]
    version, parsed = parse_date_table([header, data], 95)[0]
    assert version == "CIP-015-2"
    assert parsed.requirement == "R1.1"
    assert parsed.requirement_date == date(2029, 10, 1)
    assert parsed.part_date == date(2030, 1, 1)
    assert parsed.page == 95
    assert parsed.status == "Subject to Future Enforcement"
    data[4] = "1.2. DO NOT USE"
    assert parse_date_table([header, data], 95)[0][1].source_note == "DO NOT USE"
    data[6] = "See implementation plan"
    with pytest.raises(ValueError):
        parse_date_table([header, data], 95)


def test_schedule_cannot_attach_to_another_catalog_version() -> None:
    with pytest.raises(ValidationError, match="exact catalog version"):
        CatalogDocument(standard_id="CIP-015", version="1", sha256="b" * 64,
            source_url="https://www.nerc.com/test.pdf", retrieval_date=date(2026, 9, 11),
            fingerprinted_on=date(2026, 9, 17), effective_date_schedule=schedule([row()]))


@pytest.mark.parametrize("part_date,expected", [(None, "2029-10-01"), ("2030-01-01", "Multiple dates")])
def test_schedule_is_rendered_with_requirement_dates_and_provenance(part_date: str | None, expected: str) -> None:
    payload = schedule([row(), row(2, requirement="R1.1", part_date=part_date)]).model_dump_json()
    script = f'''
from nerc_compliance_intelligence.app import demo_dashboard_data, _render_review_package
from nerc_compliance_intelligence.effective_dates import EffectiveDateSchedule
data = demo_dashboard_data()
data["uploaded"] = data["uploaded"].model_copy(update={{"effective_date_schedule": EffectiveDateSchedule.model_validate_json({payload!r})}})
_render_review_package(data)
'''
    app = AppTest.from_string(script, default_timeout=30).run()
    assert not app.exception
    assert app.metric[1].value == expected
    assert any("Synthetic dates.pdf" in element.value for element in app.text)
    date_column = app.get("column")[1]
    assert date_column.metric[0].label == "Standard effective date"
    assert date_column.text[0].value == "Source: Synthetic dates.pdf — page(s) 95"
    assert not any(element.label == "Effective-date source and requirement details" for element in app.expander)
