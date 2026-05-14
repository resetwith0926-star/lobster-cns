Repair the provided output into valid JSON for contract_version `content_review.v1`.

Rules:
- Do not add new strategy or claims.
- Only repair structure, enums, missing fields, and invalid types.
- Keep content meaning as close as possible.

Required fields:
- contract_version: "content_review.v1"
- status: "pass" | "needs_revision" | "blocked"
- overall_score: integer 0-100
- tone_score: integer 0-100
- medical_safety_score: integer 0-100
- cta_safety_score: integer 0-100
- discipline_score: integer 0-100
- risk_flags: array
- suggested_rewrites: array
- review_summary: string
- approval_recommendation: "approve" | "revise" | "block"

If uncertain, choose conservative defaults:
- status: "needs_revision"
- scores: 60
- risk_flags: []
- suggested_rewrites: []
- review_summary: "Needs revision for safer and clearer wording."
- approval_recommendation: "revise"

Return JSON only.
