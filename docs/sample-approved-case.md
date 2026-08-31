# Sample Approved Case — Fictional Demonstration

## Scope

- Utility: Northstar Grid Services (fictional)
- Asset: `SUB-ALPHA-RTU-01` (synthetic)
- Standard boundary: CIP-010-5 primary; CIP-007-6 supporting
- Requirement ID: `Synthetic demo reference` for the fake automated demonstration; real runs must use retrieved local requirement IDs and citation metadata.

## Review outcome

The synthetic evidence record and simulated baseline are reviewed. The draft control and all remediation steps retain their linked retrieved requirement ID. The example result is a potential review lead, not a compliance finding.

## Demonstration sequence

| Stage | Demonstration event | Safe outcome |
|---|---|---|
| Failure | A missing synthetic requirement reference returns an empty result. | The graph does not invent a requirement. |
| Recovery | The graph makes its one bounded validation repair using the known synthetic reference. | Retrieval resumes only when the repaired reference is present. |
| Interrupt | The draft remediation plan reaches the human approval interrupt. | No workflow exists yet. |
| Human edit | The reviewer selects **edit** once. | The draft is visibly revised and returns to the same approval pause. |
| Approval | The reviewer selects **approve** with a role and timestamp. | The export guard is eligible to run. |
| Export | The guarded tool writes one synthetic JSON record under `outputs/workflows/`. | No external ticket, GitHub update, or operational action occurs. |

## Human approval record

| Field | Demonstration value |
|---|---|
| Decision | Approve |
| Reviewer role | Compliance manager |
| Purpose | Allow synthetic local workflow export only |
| Operational action | None |
| Automatic gap closure | Disabled |

## Expected safe outcome

After the graph interrupt receives the explicit approval, the guarded export tool may write one synthetic JSON workflow below the ignored `outputs/workflows/` directory. It cannot write outside that directory, to GitHub, to a ticketing system, or to an operational asset.
