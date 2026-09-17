# Effective-date reference integration

## Source and meaning

Source: `CIP us-effective-date-status-functional-applicability.pdf`, supplied in
the approved corpus. This is a 121-page reference export with 596 declared entries.
The app records the exact source file fingerprint, extraction date, page number,
and row ID. Extraction date is not an assertion that the source is current.

The packaged catalog contains a schedule for each matching exact standard/version.
Only an approved upload fingerprint receives that schedule. A renamed file may
match by bytes; a different version never borrows the date of a similar name.
No source PDF, private filesystem path, or confidential information is packaged.

## Display rules

| Source data | Summary card |
|---|---|
| All listed requirement and explicit part dates agree | The common ISO date |
| Different dates | Multiple dates, with a full Multiple effective dates caption |
| Some requirement dates missing | Incomplete dates |
| All dates blank | Not specified |
| Annotated rows, including DO NOT USE | Review date notes |
| No matched date metadata | Not verified |

Source notes take precedence over a simplified date. No Parts rows are retained
for audit but are not counted as separate requirements. A blank part-date cell is
retained as missing in the catalog; the inline requirement view uses an explicit
part date when present, otherwise its recorded requirement date.
Inactive dates and status are retained, not used to silently filter historical rows.

The source document name and page numbers appear directly under Standard effective
date, followed by the jurisdiction and snapshot notice. There is no separate
effective-date section. Individual dates and citations remain in Requirements and sources.

The summary concerns the entire exact standard version listed in the reference,
not a claim that every listed requirement applies to the selected organization.
All imported dates are scoped to the United States. No Canadian applicability or
jurisdiction is inferred from a selected Regional Entity.

## Example from the supplied snapshot

CIP-015-2 has requirement dates of 2029-10-01 for R1, R2, and R3 and the same
explicit date for parts R1.1, R1.2, and R1.3 (page 95, rows 589-596).
The source labels these rows Subject to Future Enforcement. This is a report of
the supplied reference, not a fresh legal or regulatory determination.

## Refresh procedure

Use `extract_date_schedules(Path(...))` in `effective_dates.py` against an approved
replacement reference export. It returns typed schedules without writing files.
Review all extracted rows and version matches before applying catalog changes.
The parser validates the declared row count and column names and rejects unknown
date syntax instead of guessing. Update the cache policy when packaged metadata
changes; test and approve publication separately.

Synthetic tests cover date-column selection, phased and missing dates, source
notes, version mismatches, and rendered dates/citations. These tests establish
software behavior, not the current legal accuracy of the supplied reference.

## Verification results

- Full offline suite: 206 passed; targeted date/catalog/UI tests: 38 passed.
- Offline evaluations: 15/15 passed, external tracing disabled.
- All 596 source rows extracted across 29 versions; 481 rows attached to the 24
  exact versions already in the approved fingerprint catalog.
- Real CIP-015-2 and CIP-010-5 uploads returned the expected source-snapshot dates
  without a local corpus database. Page 95 was rendered and visually checked.
- Offline wheel build contains all 24 schedules and no PDF or `.env` files.
- Local health check and diff whitespace check passed. Not pushed or deployed.
