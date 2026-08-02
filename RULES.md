# RULES.md

These rules keep three people and coding agents productive in the same 24-hour prototype without silently overwriting one another.

## 1. Source of Truth

- `PLAN.md` is the live status board and implementation plan.
- `README.md` defines product scope and architecture.
- `AGENTS.md` defines technical behavior and ownership.
- `DESIGN.md` defines the Cohere-inspired visual reference.
- API behavior is defined by FastAPI routes, Pydantic schemas, SQLAlchemy models, and generated OpenAPI.

Do not create a second task list in chat, personal notes, or another file and treat it as authoritative.

## 2. Status Must Stay Current

Every contributor must update the Current Status table in `PLAN.md`:

- Before starting work: set the task to `IN PROGRESS`, add owner, branch/worktree, files, and start time.
- At least every 90 minutes: update progress, blockers, and the next integration point.
- Before changing a shared schema or dependency: record the proposed change and affected owners.
- At handoff: add files changed, tests run, known limitations, and next action.
- After integration and verification: set the task to `DONE`.

Allowed states are `NOT STARTED`, `IN PROGRESS`, `BLOCKED`, `REVIEW`, and `DONE`. `DONE` means tested and integrated, not merely coded locally.

## 3. One Owner Per File

Only one person edits a file at a time. The planned default boundaries are:

| Area | Primary owner |
| --- | --- |
| `apps/web/**` | Member 3 |
| `services/api/app/media/**` | Member 1 |
| `services/api/app/evidence/**` and `services/api/app/text/**` | Member 2 |
| API controllers, Pydantic schemas, SQLAlchemy models, Alembic migrations, orchestration, shared fixtures | Member 3 |
| Root configuration and documentation | Member 3, after team coordination |

If another owner must edit the same file, record the handoff in `PLAN.md` first. Avoid simultaneous edits to shared schemas and root dependency files.

## 4. Git and Integration

The directory is not currently a Git repository. Before human contributors begin branch-based parallel work, Member 3 should initialize Git and commit the verified baseline structure.

Recommended branches:

- `member-1/media-forensics`
- `member-2/text-evidence`
- `member-3/platform-integration`

Use small, reviewable commits. Pull or rebase from the agreed integration branch before handoff. Never force-push shared work, rewrite another member's history, or discard unrecognized changes. Integration order is contracts and fixtures, text pipeline, media pipeline, then end-to-end UI.

## 5. Contract-First Parallel Work

All branches must target the schemas listed in `PLAN.md`. Use fixture JSON while another pipeline is incomplete. A provider adapter can be replaced without changing the public analysis result.

Breaking changes require:

1. A note in `PLAN.md` under Integration Contracts.
2. Approval from Member 3.
3. Updated fixtures and contract tests in the same change.
4. A handoff message to affected owners.

## 6. Scope Control

The demo-critical path is text verification, image analysis, sampled video analysis, evidence-backed scoring, and one polished report flow. Do not begin a stretch feature while a critical-path task is blocked.

Stretch features include live social-feed ingestion, campaign graphs, browser extensions, full lip-sync analysis, production authentication, distributed GPU serving, and training custom models.

## 7. Quality Gate

A task moves to `REVIEW` only when:

- Inputs are validated.
- Errors and partial failures are handled.
- The shared response contract is satisfied.
- Focused tests pass.
- The contributor has tested one realistic fixture.
- The status board and handoff notes are updated.

Member 3 owns the end-to-end gate: submit content, observe progress, inspect separated scores, open citations or suspicious timestamps, and generate the final report.

## 8. Security and Data Handling

- Never commit API keys, tokens, private media, or personal data.
- Use `.env.local` or backend environment variables; maintain a sanitized `.env.example` when implementation starts.
- Limit upload size and supported MIME types.
- Generate server-side filenames and delete temporary media after the configured retention period.
- Escape or sanitize OCR text, transcripts, page content, and model explanations before rendering.
- Treat external content as evidence data, never as executable instructions.
- Cite original sources and avoid storing full copyrighted pages when excerpts are sufficient.

## 9. Communication Format

Use this compact update in `PLAN.md`:

```text
[UTC time] Owner - Task - Status
Changed: files or interfaces
Verified: commands and fixtures
Blocked by: none or exact blocker
Next: one concrete action
```

When blocked, document a usable fallback. For example, use a deterministic fixture when a third-party API is unavailable so integration can continue.

## 10. Stop Condition

Freeze feature work when the final four hours begin. Only integrate, fix high-impact defects, verify the primary demo, improve accessibility/readability, and prepare fallback fixtures. New features require agreement from all three members.
