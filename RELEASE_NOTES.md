# Lobster CNS Release Notes

## v0.1.5 - Content Quality Review Workflow Checkpoint

Release date: 2026-05-11  
Project: `lobster-cns`

### v0.1.5 Summary
- Added a local, governance-safe content quality review workflow for drafts.
- Quality review is advisory only and does not auto-approve, auto-publish, or change external state.
- Maintained local-first operation and strict no-integration boundaries.

### Phase A: Content Quality Review Data Layer
- Added `ContentDraftReview` model and schemas.
- Added SQLite-safe migration guard for `content_draft_reviews` (idempotent, non-destructive).
- Added model/schema/migration tests.

### Phase B: ContentQualityReviewService + Prompts
- Added prompt files:
  - `prompts/content_quality_review_system.md`
  - `prompts/content_quality_review_repair.md`
- Added service:
  - `ContentQualityReviewService.review_draft`
  - `get_latest_review`
  - `list_reviews`
- Added JSON repair handling for invalid review outputs.
- Added structured persistence:
  - scores
  - `risk_flags_json`
  - `suggested_rewrites_json`
  - `review_summary`
  - `raw_review_json`
- Added event logs:
  - `content_quality_review_started`
  - `content_quality_review_completed`
  - `error` (on failure path)

### Phase C: Quality Review API
- Added admin-protected API endpoints (`X-Admin-Secret` required):
  - `POST /drafts/{draft_id}/review-quality`
  - `GET /drafts/{draft_id}/reviews`
  - `GET /draft-reviews/{review_id}`
- API behavior remains local-only and advisory:
  - no draft auto-approval
  - no draft auto-publish
  - no external platform action

### Phase D: Quality Review Dashboard
- Updated draft detail page (`/dashboard/drafts/{draft_id}`) to show:
  - latest quality review result
  - status (`pass | needs_revision | blocked`)
  - all review scores
  - risk flags and suggested rewrites
  - review summary and reviewer/time
- Added dashboard action:
  - `POST /dashboard/drafts/{draft_id}/review-quality`
  - runs review then redirects back to draft detail
- Added legacy-safe rendering when no review exists.
- Added explicit dashboard messaging:
  - quality review is advisory only
  - approved still means human use/copying only
  - system does not publish externally

### Release Gate (v0.1.5)
- Verified `git status --short` (only parent-directory untracked files outside `lobster-cns`).
- Verified full test suite.
- Verified quality review dashboard rendering for no-review and reviewed cases.
- Verified dashboard quality review action works.
- Verified quality review does not change `ContentDraft.status` automatically.
- Verified quality review does not auto-approve drafts.
- Verified no external publishing behavior exists.
- Verified required quality review API endpoints exist and are admin-protected.
- Verified no external integration routes:
  - `/facebook`, `/instagram`, `/telegram`, `/line`, `/x`, `/n8n`
- Verified only `ceo_agent` enabled; placeholders remain disabled.
- Verified no auto-posting / auto-commenting / auto-DM flows exist.

## Test Result
- `pytest`: **151 passed**.

## Safety Constraints Preserved
- `simulation_only` remains true.
- `requires_human_approval` remains true.
- `approval_checklist.requires_human_review` remains true.
- `approval_checklist.external_action_blocked` remains true.
- No external platform execution introduced.
- Quality review remains advisory and local-only.

## Known Limitations
- No external publishing integrations (by design).
- No real worker-agent execution (by design).
- Content quality review output quality depends on LLM response quality.
- Dashboard actions are local workflow actions, not deployment/publishing actions.

## Recommended Next Step
- v0.1.6 can focus on human-in-the-loop editing ergonomics and quality iteration:
  - clearer review diff presentation,
  - structured revise suggestions application,
  - stronger audit trail on draft revisions,
  while preserving all current governance and no-external-action constraints.

## v0.1.4 - Content Draft & Review Workflow Checkpoint

Release date: 2026-05-10  
Project: `lobster-cns`

### Baseline: v0.1.3
- CEO Governance Core released with decision contract `ceo_decision.v1.3`.
- Task-level visibility for `primary_agent_role`, `supporting_agent_roles`, `decision_rubric`, and `approval_checklist`.
- Only `ceo_agent` enabled; all placeholder agents disabled.
- No external platform integrations.

### Phase A: ContentDraft Data Layer
- Added `ContentDraft` data model and schemas.
- Added SQLite-safe migration guard for `content_drafts` (idempotent, non-destructive).
- Added model/schema/migration tests.

### Phase B: ContentDraftService
- Added local draft lifecycle service:
  - create draft from task
  - get/list drafts
  - update draft status and review notes
- Added event logging for draft lifecycle (`draft_created`, `draft_status_changed`).

### Phase C: Draft Generation
- Added prompt files:
  - `prompts/content_draft_system.md`
  - `prompts/content_draft_revision.md`
- Added service methods:
  - `generate_draft`
  - `revise_draft`
- Draft generation/revision uses existing LLM provider architecture.
- Preserved safety behavior:
  - no auto-approve
  - no external publishing
  - no task lifecycle mutation

### Phase D: Draft API
- Added admin-protected draft endpoints (`X-Admin-Secret` required):
  - `POST /drafts`
  - `GET /drafts`
  - `GET /drafts/{draft_id}`
  - `POST /drafts/{draft_id}/generate`
  - `POST /drafts/{draft_id}/revise`
  - `POST /drafts/{draft_id}/status`
- API remains local workflow only; no external platform actions.

### Phase E: Draft Dashboard
- Added dashboard pages:
  - `GET /dashboard/drafts`
  - `GET /dashboard/drafts/{draft_id}`
- Added dashboard draft actions:
  - create draft from task
  - generate draft
  - revise draft
  - update status
- Updated task detail to show related drafts.
- Added explicit UX warning: approved means human use/copying only, not published.

### Release Gate (v0.1.4)
- Verified full test suite.
- Verified `ceo_agent` only enablement.
- Verified all other agents remain disabled placeholders.
- Verified no external integration routes (`/facebook`, `/instagram`, `/telegram`, `/line`, `/x`, `/n8n`).
- Verified draft workflow paths exist in app routes and are covered by tests.
- Verified no auto-posting, auto-commenting, or auto-DM functionality was introduced.

## Test Result
- `pytest`: **112 passed**.

## Safety Constraints Preserved
- `simulation_only` remains true.
- `requires_human_approval` remains true.
- `approval_checklist.requires_human_review` remains true.
- `approval_checklist.external_action_blocked` remains true.
- No external platform control or worker execution introduced.

## Known Limitations
- No real worker agents yet (placeholders only).
- No social/media platform integrations (by design).
- No auto-posting pipeline (by design).
- Dashboard actions are local workflow operations only.
- SQLite startup migration guards are used; Alembic not introduced yet.

## Recommended Next Step
- Start v0.1.5 planning focused on governance-safe editorial quality:
  - draft quality scoring and revision guidance,
  - approval ergonomics for human reviewers,
  - stricter observability around draft iterations,
  - preserve local-first and no-external-action guarantees.

## v0.1.3 - CEO Governance Core Upgrade Checkpoint

Release date: 2026-05-10  
Project: `lobster-cns`

### Baseline: v0.1.2
- Local-first FastAPI + SQLite CEO Governance Core.
- CEOAgent can receive tasks, review with DeepSeek, produce structured decisions, and write logs/memory.
- Only `ceo_agent` is enabled; all other agents remain disabled placeholders.
- No external platform integrations.

### Phase A: Decision Contract v1.3
- Upgraded CEO decision contract to `ceo_decision.v1.3`.
- Added:
  - `primary_agent_role`
  - `supporting_agent_roles`
  - `decision_rubric`
  - `approval_checklist`
- Preserved backward compatibility for v1/v1.2 payloads.

### Phase B: Persistence Compatibility
- Added task persistence support for:
  - `primary_agent_role`
  - `supporting_agent_roles_json`
- Added SQLite-safe startup migration guard (non-destructive, no Alembic yet).
- Legacy decisions are stored safely with fallbacks:
  - `primary_agent_role` defaults from `suggested_agent_role`
  - `supporting_agent_roles_json` defaults to `[]`

### Phase C: CEOAgent Output Quality
- Improved CEOAgent normalization and repair stability for v1.3 decisions.
- Enforced post-response safety constraints:
  - `simulation_only = true`
  - `requires_human_approval = true`
  - `approval_checklist.requires_human_review = true`
  - `approval_checklist.external_action_blocked = true`
- Kept `suggested_agent_role` populated for backward compatibility.

### Phase D: Dashboard Clarity
- Improved dashboard task visibility for v1.3 decision fields:
  - `primary_agent_role`
  - `supporting_agent_roles`
  - `decision_rubric`
  - `approval_checklist`
- Added legacy-safe rendering fallback on task detail pages:
  - `primary_agent_role` fallback to `suggested_agent_role`
  - `supporting_agent_roles` fallback to `[]`
  - `decision_rubric` fallback to `{}`
  - `approval_checklist` fallback to `{}`
- Kept UI simple and function-first.

### Phase E: Release Gate
- Verified working tree and full test suite.
- Verified dashboard routes and legacy rendering safety.
- Verified no external platform integration routes were introduced.
- Verified safety constraints remain enforced.

## Test Result
- `pytest`: **52 passed**.

## Safety Constraints Preserved
- `simulation_only` remains true.
- `requires_human_approval` remains true.
- `approval_checklist.requires_human_review` remains true.
- `approval_checklist.external_action_blocked` remains true.
- No external platform control or worker execution introduced.

## Known Limitations
- No real worker agents yet (placeholders only).
- No social/media platform integrations (by design).
- No browser automation execution layer.
- No Alembic migration system yet (startup guard used for SQLite compatibility).

## Recommended Next Step
- Start v0.1.4 planning as a scoped quality/refactor checkpoint:
  - finalize migration strategy (optional Alembic introduction),
  - expand decision analytics/readability in dashboard without changing core lifecycle,
  - keep governance-first safety model unchanged.
