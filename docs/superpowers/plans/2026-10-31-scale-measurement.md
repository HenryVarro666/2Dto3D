# Scale measurement implementation plan

**Goal:** Known-length calibration, two-point distance and held-out length validation, with durable documentation and bilingual visual READMEs.
**Architecture:** Separate measurement receipts over immutable V3 point-cloud GLB coordinates; backend resolves point indices; browser picks raw points without display offsets. No model change or single-view metric claims.
**Stack:** Existing FastAPI/Pydantic/SQLite, Trimesh/NumPy, React/TypeScript/Three.js. No added runtime dependency.
**Spec:** [Approved scope](../specs/2026-10-31-scale-measurement.md).
**Review focus:** Point-index parity between GLTFLoader and backend; geometry/job ownership; reference leakage; stale requests; units/labels; synthetic versus field evidence; private data exclusion.

1. Freeze base `9c202d1`, read quality ledger; create isolated worktree. Native worktree tool rejected external sourceRoot because this chat belongs to historical research directory; fallback to ignored `.worktrees/scale-measurement`. Preserve other chat's uncommitted changes.
2. RED tests for service calculations, immutable receipts, rejection cases and restart. Implement schemas, GLB coordinate resolution, persistence and API. Test model-free old/new GLB path.
3. RED tests for viewer point identity/original coordinates and measurement panel. Implement point selection, markers, session reload, error/validation forms, trilingual messages, job restoration.
4. Add deterministic authored analytic demo and frozen benchmark/report. Verify scale invariance and deliberately distorted held-out lengths. Real field precision remains unverified until independently measured inputs arrive.
5. Verify actual browser interactions and save genuine screenshots; author matching Chinese/English README and maintainable SVG/Mermaid diagrams. Update API/running/changelog/quality ledgers.
6. Fresh independent code review, full tests/lint/build/link checks, fresh clone verification. Verify private GitHub visibility; commit and push feature branch. Integrate latest concurrent quality commits safely before synchronizing main; never include unrelated dirty edits.

## Execution record

- 2026-10-31: product graph reported empty, used documented file-search fallback. User asked for measured lengths and README target via optional async questions; implementation proceeds under spec defaults. Source checkout now has other worker edits; no changes copied or reverted.

- Feature implementation and RED/GREEN complete. Independent reviewer found repeated-restore lock; added regression, revision keys for viewer and receipts, re-reviewed GREEN. Actual production browser exercised calibration, held-out check, reference rejection, trilingual state and JSON download. Full feature-tree checks 107 backend + 2 optional ML skipped / 65 frontend / build / Ruff passed. Documentation/visual provenance and failures in E05; integration and fresh-clone verification follow.
- Integrated completed E04 at e66a6d9, preserving 237f796/5e6f316 implementation/tests byte-for-byte. Resolved README and ledger conflicts by retaining E04 history plus E05 and matching English claims. Formal root main fast-forwarded only after other chat completed and checkout was clean. Full root checks: 113 backend / 65 frontend / build / Ruff / six SVGs passed. Private GitHub visibility verified; push/fresh clone follows.
