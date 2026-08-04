# VeriShield AI - 24-Hour Prototype Plan

## Planning Status

Planning is complete and the first implementation slice is integrated. Multimodal intake, validation, persistence adapters, request polling, and the responsive workspace are ready for the three specialist workstreams.

## Goal

Demonstrate an end-to-end multimodal verification flow for Indian audiences:

```text
Input -> modality analysis -> evidence retrieval -> aggregation -> calibrated scores -> cited explanation
```

The prototype succeeds when a judge can submit representative text, image, and video inputs and understand what was checked, what evidence was found, how confident the system is, and which parts require human review.

## MVP Scope

### Demo critical

- Paste text or a URL and extract one or more verifiable claims.
- Run bounded parallel evidence searches and classify evidence stance.
- Upload an image and return metadata, model risk, and suspicious-region findings when available.
- Upload a short video, sample representative frames, and return frame scores plus suspicious timestamps.
- Keep claim, media, context, source, and evidence-confidence scores separate.
- Show supporting and contradicting sources with citations.
- Produce an English explanation and one Indian-language explanation through a provider adapter.
- Provide deterministic demo fixtures when external services fail.

### Stretch

- Audio spoof detection and lip-sync scoring.
- Reverse image or keyframe search through a live provider.
- Live social-media collection and campaign clustering.
- Evidence graph visualization.
- Browser extension, authentication, and downloadable PDF reports.

### Out of scope for 24 hours

- Training a new deepfake model.
- Production-scale crawling or ingestion.
- Claims of guaranteed truth or guaranteed deepfake detection.
- Fully distributed GPU infrastructure.
- Automated decisions for elections, health, or public safety without human review.

## Three-Member Work Split

| Owner | Focus | Required deliverables | Integration output |
| --- | --- | --- | --- |
| Member 1 | Deepfake image and video | Metadata extractor, image model adapter, FFmpeg sampling, frame scoring, suspicious timestamps, fixtures, tests | `MediaAnalysisResult` |
| Member 2 | Text misinformation and evidence | Claim extraction, query fan-out, parallel source retrieval, deduplication, stance classification, source/claim score inputs, citations, tests | `TextAnalysisResult` and `EvidenceItem[]` |
| Member 3 | Overall system, agent flow, UI, and integration | Next.js workspace, FastAPI gateway, Pydantic contracts, SQLAlchemy/Supabase persistence, orchestration, progress lifecycle, score aggregation, report UI, Docker/demo setup, integration tests | `AnalysisReport` and runnable demo |

Member names should replace the role labels before implementation begins.

## Parallel Work Strategy

Hour 0-1 is a shared contract session. Member 3 creates the repository structure, schemas, fixture payloads, and one mocked end-to-end route. Members 1 and 2 then implement behind those contracts without waiting for the UI or each other.

Member 2's retrieval fan-out should use bounded concurrency, not sequential page processing:

```text
Atomic claim
  -> 3-5 targeted queries
  -> concurrent search adapters
  -> concurrent top-result fetches
  -> passage extraction and deduplication
  -> reranking and stance classification
  -> top cited evidence
```

Set concurrency limits, per-request timeouts, total time budgets, domain deduplication, and partial-result behavior. The system should retrieve useful passages rather than sending complete pages to the explanation model.

## 24-Hour Schedule

| Time | Team objective | Member 1 | Member 2 | Member 3 |
| --- | --- | --- | --- | --- |
| 0:00-1:00 | Contract freeze | Validate media schema/fixtures | Validate text/evidence schema/fixtures | Initialize repo, skeleton, schemas, fixtures |
| 1:00-5:00 | First vertical pieces | Image metadata and model adapter | Claim extraction and search adapters | Analyzer UI and mocked API lifecycle |
| 5:00-8:00 | Complete core branches | Video sampling and frame aggregation | Evidence dedupe, stance, source scoring | Orchestrator and score aggregation |
| 8:00-10:00 | Integration gate 1 | Connect media result endpoint | Connect text/evidence endpoint | Merge both into report contract |
| 10:00-14:00 | Product flow | Heat map/timeline output | Citation quality and multilingual explanation input | Evidence/results UI and progress states |
| 14:00-17:00 | Hardening | Degraded media fixtures and timing | Timeout/insufficient-evidence cases | Error states, responsive UI, accessibility |
| 17:00-20:00 | Integration gate 2 | Fix contract defects | Fix contract defects | End-to-end tests and Docker run |
| 20:00-22:00 | Demo preparation | Choose stable media examples | Choose stable claim examples | Demo script, seeded fallback, visual polish |
| 22:00-24:00 | Freeze and rehearse | Critical fixes only | Critical fixes only | Final smoke test and presentation handoff |

## Integration Contracts

These are conceptual contracts to implement as Pydantic schemas, TypeScript interfaces, and SQLAlchemy models where persistence is required.

```text
AnalysisRequest
- input?: string
- attachment?: image | video
- preferred_language: string

The API classifier derives `input_type` from a verified attachment signature, a complete
HTTP(S) URL, or text fallback. Media storage uses `analyses/{analysis_id}/input.{ext}`.

AnalysisJob
- id: string
- status: queued | preprocessing | analyzing | retrieving | scoring | completed | failed
- progress: integer 0-100
- active_stage: string
- partial_results: boolean
- error?: PublicError

EvidenceItem
- id: string
- claim_id: string
- stance: supported | contradicted | insufficient | unrelated
- title: string
- publisher?: string
- url: string
- published_at?: UTC datetime
- passage: string
- relevance: number 0-1
- source_reliability: number 0-100

MediaFinding
- kind: metadata | provenance | spatial | temporal | audio | lip_sync | context
- score?: number 0-1
- label: string
- reason: string
- region?: normalized bounding box
- timestamp_seconds?: number
- availability: available | unavailable | failed

ScoreBreakdown
- claim_credibility?: integer 0-100
- media_manipulation_risk?: integer 0-100
- context_authenticity?: integer 0-100
- source_reliability?: integer 0-100
- evidence_confidence?: integer 0-100

AnalysisReport
- job: AnalysisJob
- claims: ClaimResult[]
- media_findings: MediaFinding[]
- evidence: EvidenceItem[]
- scores: ScoreBreakdown
- verdict: supported | likely_credible | unverified | missing_context | misleading | likely_manipulated | contradicted | insufficient_evidence
- explanation: localized text
- human_review_recommended: boolean
- limitations: string[]
```

### Initial API surface

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/v1/analyses` | Submit text, URL, image, or video |
| `GET` | `/api/v1/analyses/{id}` | Poll progress and retrieve partial/final results |
| `GET` | `/api/v1/analyses/{id}/report` | Retrieve normalized final report |
| `GET` | `/api/v1/health` | Confirm API and provider readiness |

Polling is the default for the prototype. WebSockets are optional and should not delay the critical path.

## Planned Repository Structure

```text
VeriShield/
|-- apps/
|   `-- web/                    # Next.js application
|-- services/
|   `-- api/
|       |-- app/
|       |   |-- modules/        # FastAPI domain modules
|       |   |   `-- analyses/   # Router, service, schemas, repository
|       |   |-- core/           # Settings and error handling
|       |   |-- database/       # SQLAlchemy base and async sessions
|       |   `-- storage/        # Supabase Storage adapter
|       |-- alembic/            # PostgreSQL migrations
|       `-- tests/
|-- fixtures/                   # Safe deterministic demo inputs/results
|-- infra/                      # Docker and local services
|-- AGENTS.md
|-- DESIGN.md
|-- PLAN.md
|-- README.md
`-- RULES.md
```

## Integration Gates

### Gate 1 - Hour 10

- All branches emit fixture-compatible schemas.
- Text flow returns at least one claim and cited evidence.
- Image flow returns metadata and a risk result.
- Video flow returns sampled frames and timestamps.
- UI can render each result without provider-specific code.

### Gate 2 - Hour 20

- One end-to-end text, image, and video scenario passes.
- External failure falls back to a clearly labeled deterministic demo response.
- Verdict dimensions remain separate.
- Mobile and desktop primary flows are readable and keyboard accessible.
- Demo can start from documented commands on a clean environment.

## Technology Decisions

- Monorepo-shaped repository with a Next.js frontend and FastAPI backend.
- Pydantic schemas and generated OpenAPI are the HTTP contract authority; SQLAlchemy owns persistence models.
- REST polling for job progress in the MVP.
- Asyncio-based retrieval with bounded concurrency and explicit timeouts.
- Pretrained model adapters and provider APIs, never model training during the sprint.
- Supabase PostgreSQL stores analysis jobs and input metadata through SQLAlchemy.
- Supabase Storage is the target for uploaded media; local temporary storage remains the no-credential development fallback.
- A process-local FastAPI job service is sufficient for the initial intake prototype; a durable Python task queue is deferred until analysis jobs require workers.

## Risks and Fallbacks

| Risk | Mitigation |
| --- | --- |
| Deepfake model download or GPU failure | Cache one verified model; keep deterministic media fixtures and CPU-safe metadata/frame analysis |
| Search API rate limit or no key | Use cached evidence fixtures and clearly mark them as demo data |
| Slow video processing | Limit duration/size, sample adaptively, show progress, and precompute the demo case |
| False confidence | Calibrate labels, expose missing evidence, and recommend human review |
| Three-way merge conflict | Contract freeze, file ownership, small commits, and scheduled integration gates |
| Scope expansion | Protect demo-critical tasks and freeze features at hour 20 |
| Harmful or private uploads | MIME validation, size limits, generated filenames, short retention, and no committed user media |

## Current Status

Update this table according to `RULES.md` throughout the sprint.

| Workstream | Owner | Status | Branch/worktree | Files or contract | Last update | Blocker / next action |
| --- | --- | --- | --- | --- | --- | --- |
| Planning and documentation | Codex | DONE | Current workspace | Root Markdown files | 2026-08-02 | Keep status current during specialist work |
| Repository initialization and contracts | Wegener + Codex | DONE | Shared workspace | FastAPI modules, Pydantic schemas, SQLAlchemy models | 2026-08-02 | Configure remote Supabase URL and apply the Alembic migration |
| Media forensics | Rajath | NOT STARTED | `abishekpriyanm369/nod-7-build-image-and-video-deepfake-forensic-analysis-module` | `MediaAnalysisResult`, image/video forensic module | 2026-08-03 | Start Linear NOD-7 and select a CPU-safe pretrained model adapter |
| Text and evidence | Sivabalan | REVIEW | `abishekpriyanm369/nod-8-build-claim-verification-web-evidence-retrieval-and` | `claim_extractor.py`, `query_planner.py`, `evidence_retriever.py`, `stance_classifier.py`, `credibility_scorer.py` | 2026-08-03 06:13 UTC | Pipeline implementation is complete; install backend test dependencies to run pytest and ruff in this workspace |
| UI, orchestration, and integration | Anscombe + Codex | DONE | Shared workspace | Unified Next.js composer, classifier-owned API contract | 2026-08-03 | Extend lifecycle UI when analysis result contracts land |
| End-to-end verification and demo | Codex | IN PROGRESS | Shared workspace | Unified intake scenarios | 2026-08-03 | Add text and media result fixtures next |

## Activity Log

Append compact updates here using the format in `RULES.md`. Keep the newest entry first.

```text
[2026-08-03 06:13 UTC] Codex - Text evidence pipeline build - REVIEW
Changed: added claim extraction, query planning, secure evidence retrieval, stance classification, deterministic scoring, provider adapters, and fixture-backed pipeline smoke coverage
Verified: `python -m compileall app tests` and a direct fixture pipeline smoke run (`1 3 100 supported`)
Blocked by: `pytest` and `ruff` are not installed in the bundled Python runtime, so the full backend test suite could not run here
Next: install the backend dev dependencies, run pytest and ruff, and wire the pipeline into the analysis service when the shared report contract is ready

[2026-08-03 05:58 UTC] Codex - Text evidence pipeline build - IN PROGRESS
Changed: claimed the member-2 text/evidence workstream and began implementing claim extraction, query planning, secure retrieval, stance classification, and deterministic scoring modules
Verified: repository layout, current API contract, and backend test surface
Blocked by: none; the pipeline can start with offline fixtures and local adapters
Next: add the new modules, wire deterministic fixtures, and run focused backend tests

[2026-08-03] Codex - Claim verification handoff - NOT STARTED
Changed: assigned claim extraction, bounded web evidence retrieval, stance analysis, and credibility scoring to Sivabalan in Linear NOD-8
Verified: issue is linked to the Z-AI project, proof-of-concept milestone, and sibling media issue NOD-7 with High priority
Blocked by: provider credentials are not confirmed; deterministic fake providers allow local implementation to start
Next: Sivabalan starts NOD-8, confirms provider adapters, and marks this workstream IN PROGRESS

[2026-08-03] Codex - Media forensics handoff - NOT STARTED
Changed: assigned image/video deepfake forensic MVP to Rajath in Linear NOD-7 with module boundaries, lifecycle integration, tests, and acceptance criteria
Verified: issue is linked to the Z-AI project and proof-of-concept milestone with High priority
Blocked by: none; implementation has not started
Next: Rajath starts NOD-7, selects the model adapter, and marks this workstream IN PROGRESS

[2026-08-03] Codex - Unified classified intake - DONE
Changed: replaced manual modality tabs with one prompt and optional media attachment; storage keys now use analyses/{analysis_id}/input.{ext}
Verified: backend Ruff and 12 Pytest cases; frontend lint and unit tests
Blocked by: media-forensics and evidence workers are not connected yet
Next: connect classifier routes to the text, image, and video worker modules

[2026-08-02] Codex - Backend correction to FastAPI - DONE
Changed: replaced NestJS/Prisma runtime with FastAPI, Pydantic, SQLAlchemy async, Alembic, and Supabase Storage
Verified: Ruff, strict MyPy, six Pytest cases, live text/URL/image requests, and Next.js browser submission
Blocked by: remote Supabase credentials are not configured, so local fallbacks are active
Next: connect Member 1 media forensics and Member 2 text/evidence services through Python module interfaces

[2026-08-02] Codex - Multimodal intake vertical slice - DONE
Changed: integrated Next.js intake UI and the original intake contract
Verified: frontend lint/typecheck/unit/build; live text, URL, and image submissions; desktop and mobile browser checks
Blocked by: remote Supabase credentials are not configured, so local fallbacks are active
Next: connect Member 1 media forensics and Member 2 text/evidence results behind the existing analysis lifecycle

[2026-08-02] Codex - Parallel agents spawned - IN PROGRESS
Changed: assigned Anscombe to apps/web and Wegener to services/api
Verified: disjoint write scopes and shared POST/GET analysis contract
Blocked by: none for local development; remote Supabase remains unconfigured
Next: review and integrate both agent outputs

[2026-08-02] Codex - Initial implementation kickoff - DONE
Changed: an incorrect NestJS/Prisma inference was made and later replaced by the required FastAPI stack
Verified: Supabase connection guidance reviewed
Blocked by: remote Supabase credentials are not available
Next: run frontend and backend agents against separate write scopes

[2026-08-02] Codex - Planning and documentation - DONE
Changed: AGENTS.md, RULES.md, PLAN.md, README.md
Verified: source PDF content, DESIGN.md alignment, local links, ASCII, and document consistency
Blocked by: none
Next: wait for the project owner's implementation instruction
```

## Decisions Needed for the Next Slice

- Replace Member 1, Member 2, and Member 3 with names.
- Confirm Supabase pooled and direct database URLs plus backend-only storage credentials.
- Confirm available LLM, search, fact-check, translation, and reverse-image provider credentials.
- Select and pre-download the image/video model that runs on the available hardware.
- Confirm whether the current 15 MB image and 150 MB video limits match the demo environment.
- Choose the Indian language used in the multilingual demo.
