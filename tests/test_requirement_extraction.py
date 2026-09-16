"""Tests for bounded extraction from a NERC Requirements and Measures section."""

from nerc_compliance_intelligence.requirement_extraction import extract_requirement_blocks


def test_requirements_are_split_across_pages_and_stop_at_measures_and_compliance() -> None:
    blocks = extract_requirement_blocks(
        [
            (1, "Introduction\nR99. A cross-reference outside section B must be ignored."),
            (
                2,
                "B. Requirements and Measures\n"
                "R1. Each Responsible Entity shall maintain a documented program.\n"
                "1.1. Include the applicable systems.\n"
                "M1. Evidence for R1 must not be included.\n"
                "R2. Each Responsible Entity shall review the program",
            ),
            (
                3,
                "at least once every 15 calendar months.\n"
                "M2. Evidence for R2 must not be included.\n"
                "C. Compliance\n"
                "R3. An appendix reference must be ignored.",
            ),
        ]
    )

    assert [block.requirement_reference for block in blocks] == ["R1", "R2"]
    assert (blocks[0].start_page, blocks[0].end_page) == (2, 2)
    assert (blocks[1].start_page, blocks[1].end_page) == (2, 3)
    assert "M1." not in blocks[0].text
    assert "M2." not in blocks[1].text
    assert "C. Compliance" not in blocks[1].text
    assert "R99" not in " ".join(block.text for block in blocks)
    assert "R3" not in " ".join(block.text for block in blocks)


def test_summary_is_plain_language_bounded_and_preserves_top_level_parts() -> None:
    block = extract_requirement_blocks(
        [
            (
                4,
                "B. Requirements and Measures\n"
                "R1. Each Responsible Entity shall document its program. "
                "[Violation Risk Factor: High] [Time Horizon: Operations Planning]\n"
                "1.1. Identify the applicable systems.\n"
                "1.2. Obtain documented approval.\n"
                "M1. Evidence follows.\n"
                "C. Compliance",
            )
        ]
    )[0]

    assert block.summary.startswith("The Responsible Entity must")
    assert "Key parts: 1.1:" in block.summary
    assert "1.2:" in block.summary
    assert "Violation Risk Factor" not in block.summary
    assert "Time Horizon" not in block.summary
    assert "Evidence follows" not in block.summary


def test_requirement_table_parts_keep_applicability_and_discard_measures() -> None:
    page_texts = [
        (
            6,
            "B. Requirements and Measures\n"
            "R1. Each Responsible Entity shall implement the applicable parts in Table R1 - Ports and Services.\n"
            "M1. Evidence must demonstrate implementation.",
        ),
        (7, "CIP-007-6 Table R1 - Ports and Services\n1.1 High Impact Systems Enable needed ports."),
        (8, "C. Compliance"),
    ]
    table_pages = [
        (
            7,
            [[
                ["CIP-007-6 Table R1 - Ports and Services", None, None, None],
                ["Part", "Applicable Systems", "Requirements", "Measures"],
                [
                    "1.1",
                    "High Impact BES Cyber Systems and associated EACMS.",
                    "Enable only needed logical ports. Document the operational need.",
                    "Example evidence. Port listing.",
                ],
            ]],
        ),
    ]

    blocks = extract_requirement_blocks(page_texts, table_pages=table_pages)

    assert [block.requirement_reference for block in blocks] == ["R1.1"]
    assert blocks[0].parent_requirement_reference == "R1"
    assert blocks[0].domain == "Ports and Services"
    assert "High Impact BES Cyber Systems" in blocks[0].applicable_systems
    assert "Enable only needed logical ports" in blocks[0].text
    assert "Example evidence" not in blocks[0].text
