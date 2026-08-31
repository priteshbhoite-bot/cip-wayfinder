# Milestone 13A — Quality Reviewer and package validation

`quality_review.py` checks a local package of retrieved requirement mappings, a draft control, a draft remediation plan, evidence analysis, and a baseline observation.

It has deliberately narrow rules: every draft requirement ID must come from retrieval; the remediation and baseline records must link to the same draft control; and incomplete or instruction-like synthetic evidence produces a warning. Results are short structured issue codes and messages, never a stack trace, source document dump, prompt, secret, approval, or compliance conclusion.

This is a pre-handoff quality check only. The existing human approval boundary remains unchanged.
