# CIP source catalog

The cloud app now carries fingerprints rather than copies of the approved PDFs.
It can recognize these exact public documents without the Windows corpus folder:

| Standard | Catalog versions |
|---|---|
| CIP-002 | 5.1a, 7, 8 |
| CIP-003 | 9, 11 |
| CIP-004 | 7, 8 |
| CIP-005 | 7 |
| CIP-006 | 6 |
| CIP-007 | 6, 7.1 |
| CIP-008 | 6, 7.1 |
| CIP-009 | 6, 7.1 |
| CIP-010 | 4, 5 |
| CIP-011 | 3, 4.1 |
| CIP-012 | 2 |
| CIP-013 | 2, 3 |
| CIP-014 | 3 |
| CIP-015 | 2 |

## What verification means

An exact SHA-256 match proves equality with a previously approved document, not
legal applicability or current enforcement. Each entry records its exact version,
official NERC URL, prior retrieval date, fingerprint date, and approval basis.
The catalog is packaged in `src/nerc_compliance_intelligence/cip_source_catalog.json`.
It contains no PDF text, credentials, local paths, or uploaded user data.

The source of this snapshot is the existing approved local corpus manifest.
Attempts to re-fetch its 24 explicit official URLs were rejected by the remote
server. Therefore these entries are not represented as newly remotely verified.
The [official CIP directory](https://www.nerc.com/standards/reliability-standards/cip)
is the starting point for a future administrative refresh, not a runtime crawler.

## Scope and limitations

- The parser is not restricted to CIP-007 and CIP-010. It extracts source-bounded
  requirements and table parts and passes their IDs/text to the existing drafter.
- Automated tests use synthetic documents for every catalog standard/version,
  plus the existing table, page-boundary, and nested-part extraction tests.
  These are not an SME assessment of the quality of every generated control.
- Historical, newly published, regional, or revised PDF bytes are not all covered.
  A newer version is never silently replaced by a catalog version.
- A catalog miss can still pass the existing NERC content-marker checks; that
  path is heuristic content validation, not proof of publisher identity.
  Low-signal unknown PDFs stop with a request for source verification.
- No runtime network request is made to validate an upload. Cloud processing
  takes place on the hosting server, not inside the visitor's browser.
- Existing UI local-only privacy wording must be corrected before treating the
  app as a production public service. Only authorized public documents may be used.

## Adding another approved version

1. Obtain the exact public PDF from its official NERC page; retain its source URL.
2. Review its identity, version, publication context, and permission to use it.
3. Compute SHA-256 for the approved bytes. Add a typed catalog entry with truthful
   provenance and dates; do not infer effective dates or jurisdictional status.
4. Test successful matching, renamed uploads, changed bytes, and extracted version.
5. Review and approve publication of the catalog update. A deployed app needs the
   updated catalog/code committed and pushed before it can recognize that file.

No website publication or deployment was performed by this implementation.

## Verification results

The catalog now also carries exact-version U.S. requirement-date schedules from
the user-supplied reference export. See [effective-date integration](effective-date-integration.md)
for provenance, display rules, and limitations. Dates are not live regulatory checks.

- Full offline suite: 196 passed.
- Offline evaluations: 15/15 passed, tracing disabled.
- Manual cloud-path check: all 24 approved real PDFs matched the packaged catalog,
  retained their versions, and generated structurally valid draft packages with
  a deliberately absent corpus database. No PDF bytes were transmitted.
- Offline wheel build: catalog present with 24 entries; no PDFs or `.env` files
  included. These checks do not establish completeness of NERC coverage or SME
  approval of the generated content.
