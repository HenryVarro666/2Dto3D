# V2 Interactive Components Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish V2 with guided box/positive/negative-point refinement and single/multiple equipment detection scope.

**Architecture:** Retain the V1 local API/worker/viewer. Add immutable refinement records and a synchronous HTTP refinement boundary scheduled on the existing bounded executor; the browser maintains an isolated draft with one in-flight request and a coalesced latest revision. Guided masks are trusted only by server-side ID, while geometry remains an explicitly relative schematic.

**Tech Stack:** Python 3.12, FastAPI/Pydantic, SQLite, PyTorch/Transformers SAM 2.1, OpenCV/Pillow, React/TypeScript/Three.js.

**Spec:** `docs/superpowers/specs/2026-10-31-v2-interactive-components.md` (user-approved feature scope).

## Global Constraints

- Canonical root remains `/Users/caochao/Documents/2Dto3D`; implementation worktree is `.worktrees/v2-interactive`.
- Preserve Chinese/English/Spanish and current request/selection/edit identity guarantees.
- Keep one bounded inference executor, local ignored photos/weights/runtime, no model training or remote inference.
- Default `scene_mode='single'` and SAM tiny preserve V1 behavior; multiple mode removes the one-cabinet restriction.
- Keep manual fallback explicit; never fabricate masks, actual dimensions, precision or complete BOM claims.
- Do not interrupt the user's V1 server until V2 is verified and ready to replace it.

## Review Focus

- Stale responses after photo replacement or fast point edits must never confirm an old mask.
- A refinement ID from another image or with mismatched bbox must be rejected before job creation.
- Busy inference, empty masks or model failures must retain the complete editable draft and box fallback.
- Multi-island thin masks and holes must survive PNG storage and manual rebuild rather than taking only the largest contour.
- Existing V1 results/database and untouched automatic evidence must still load and rebuild.

---

### Task 1: Detection scope and durable contracts

**Files:** `services/api/src/pv3d/{schemas,store,app,perception}.py`, `services/api/tests/test_{api,perception}.py`.

**Interfaces:** `JobRequest.scene_mode: Literal['single','multiple']='single'`; `Result.scene_mode` same default; `GroundingDetector.detect(image,on_progress=None,scene_mode='single')`; `normalize_predictions(...,scene_mode='single')` keeps the existing single rule and all NMS-supported candidates in multiple mode.

- [ ] Write tests: two cabinet predictions return one by default and two in multiple mode; API sends/records selected scope and rejects invalid mode; V1 requests retain defaults.
- [ ] Run `.venv/bin/python -m pytest services/api/tests/test_api.py services/api/tests/test_perception.py`; witness missing-feature failures.
- [ ] Implement scope propagation without changing prompts or thresholds, preserving existing component limit.
- [ ] Run the same tests and the backend suite; commit `feat: add single and multiple equipment scope`.

### Task 2: Guided SAM boundary and mask provenance

**Files:** create `services/api/src/pv3d/refinement.py`, tests `test_refinement.py`; modify perception/schemas/store/app.

**Interfaces:**
- `RefinementRequest={asset_id,bbox:[x1,y1,x2,y2],points:[{x,y,label:0|1}]}`; normalized finite coordinates, max 64 points, positives inside bbox.
- `Refinement={id,asset_id,bbox,geometry_bbox,points,mask_polygons,mask_url,model,timings}`; geometry bbox and polygons are derived by server from a real mask clipped to the prompt box.
- `POST /api/refinements -> Refinement`, `GET /api/refinements/{id}/mask.png` supplies transparent preview; full binary mask and JSON retained locally.
- `GroundingDetector.refine(image,bbox,points,cache_key)->dict` returns binary mask/model/timings. Reuse bounded (2-image) SAM image embedding cache, with device/checkpoint in its identity.
- `ManualComponent.refinement_id?:str`; `Detection.mask_polygons?:...` plus legacy `mask_polygon`; manual job validates referenced asset and exact stored geometry bbox, then reads authoritative mask evidence. No client polygons accepted.
- `PV3D_SAM_SIZE=tiny|small|base-plus|large` selects pinned allowlisted model revisions at server start; default tiny. Refine works independently of DINO loading.

- [ ] Write tests for finite prompts, point limits, empty result, clipped bbox, multiple contours/holes, immutable storage/reload, cross-image and bbox-mismatch rejection, and unchanged/refined/manual source evidence.
- [ ] Run these tests first; witness missing endpoint/contract failures.
- [ ] Implement storage (additive table migration), mask serialization and shared executor scheduling with existing capacity limit; error response is actionable and exposes no paths/stack.
- [ ] Add no-download adapter tests using real Torch contexts and a fake loaded SAM boundary, checking cached embeddings and prompt forwarding; use cached tiny model for real verification later.
- [ ] Run `.venv/bin/python -m pytest`; commit `feat: add durable guided SAM refinements`.

### Task 3: Annotation workflow, overlays and three-language UI

**Files:** create `apps/web/src/core/annotation.ts`, `components/AnnotationPanel.tsx`, tests; modify API types/client, App, PhotoPanel, ComponentList, workflow, translations and styles.

**Interfaces:** `WorkbenchApi.refine(input,signal?) -> Promise<Refinement>`; manual job payload forwards refinement ID only. `useAnnotation(api)` owns draft/version/pending points/result/error/timer; `start(asset,bbox,component?)`, `addPoint(point,label)`, `undo()`, `clearPoints()`, `retry()`, `cancel()`, `confirm(useBox=false)`.

- [ ] Write tests: auto request after box; positive/negative point coordinates; undo/clear; only latest mask may confirm; coalesce edits behind one request; cancel/replacement discards stale responses; fallback contains no forged mask; language switching keeps draft and pending operation.
- [ ] Run `npm --prefix apps/web test` and witness failures.
- [ ] Implement draft UI with separate confirmation and box fallback; new objects are appended only on confirmation, existing ones keep IDs. Draw bbox, preview PNG, positive/negative point markers; regular mask boundaries also visible for selected components.
- [ ] Add translated scope selector and explicit re-recognize action; selection alone never launches a task or discards edits.
- [ ] Preserve mask references for unchanged geometry across rebuilding and language switching. Label/category edits do not invalidate a valid mask; new box draft produces new evidence.
- [ ] Run frontend tests and production build; commit `feat: add guided annotation and equipment scope controls`.

### Task 4: Real verification, model comparison and V2 release

**Files:** README, AGENTS, docs/{running,api-contract,verification,i18n}, new docs/v2/model-options.md, CHANGELOG, version metadata.

- [ ] Verify cached tiny SAM over a real photo: initial box, added positive/negative prompts, persisted PNG and manual GLB containing stable IDs; do not claim accuracy without ground truth.
- [ ] Browser QA on a separate local port/data directory: three languages, draft corrections, cancellation/fallback, single/multiple selection, downloads, long text and keyboard controls; save ignored screenshots.
- [ ] Document official SAM 2.1 tiny/large, detector alternatives and SAM 3, model licensing/environment constraints and an explicit controlled comparison protocol. Larger checkpoints are selectable but untested unless actually run.
- [ ] Run `make test`, `make build`, Ruff and `git diff --check`; request one independent whole-branch review and fix concrete important findings with RED→GREEN coverage.
- [ ] Set V2 metadata, publish verified commits/release `v2.0.0`, keep `v1.0.0` immutable, and update/start the canonical workbench after user-state-safe handoff. Record verified bounds in docs.
