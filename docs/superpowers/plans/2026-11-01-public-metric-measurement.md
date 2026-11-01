# Public metric measurement evaluation implementation plan

> **For agentic workers:** Use superpowers:executing-plans for inline execution and one fresh whole-branch review. Preserve the user's authorization to finish, update the web and push the private repository.

**Goal:** Evaluate the existing one-length calibration and two-point measurement on public real multi-view photographs with independent metric reference geometry.

**Architecture:** ETH3D training photographs enter the pinned VGGT worker unchanged. Laser-derived depths and calibrated camera rays define reference lengths after inference; they never enter VGGT. Export the predicted point map through the normal GLB writer and call the existing measurement API with vertex indices. Publish an immutable compact result manifest and a trilingual web results panel; keep raw input and generated geometry ignored.

**Tech stack:** Existing Python/NumPy/SciPy/Pillow/Trimesh/FastAPI; existing React/TypeScript/Vitest; local pinned VGGT runtime. No new model or account.

**Spec:** User request to continue the interrupted feature, find public metric multi-angle photos, validate independent lengths, retain problems/improvements/results and sync web/private GitHub; existing [measurement contract](../../measurement/README.md).

## Global constraints

- Baseline origin/main `517d04c`; use isolated `eval/public-metric-measurement` worktree, leaving the separate E06 run untouched.
- Experiment E07. Reference category is laser-derived metric ground truth, not a visible physical ruler, a CAD nominal size or field inverter certification.
- Two scenes: ETH3D `pipes` and `kicker`; choose overlapping real views and endpoint pixels before viewing predictions. Freeze selection and hashes before inference.
- One calibration segment per scene; at least two different held-out segments. Do not refit using check lengths or discard a valid high-error check.
- Do not treat COLMAP triangulated points as measured ground truth. Original distorted photos must use the matching distorted depth and THIN_PRISM_FISHEYE camera.
- Test 336 and 518 input sizes on the same selected photos/endpoints as an explicit resolution comparison, preserving each run. Do not tune per scene.
- Report reference sampling support, depth-edge exclusions, pixel quantization, API/GLB consistency and uncontrolled uncertainty. No claimed submillimeter reference accuracy.
- Model timing is subprocess wall time including load/inference/export, excluding download/browser; measurement timing includes parsing and SQLite. Distinguish them.
- Chinese/English README and zh/en/es UI stay synchronized; raw photos, arrays, point clouds and database stay ignored.

## Review focus

- A distortion or depth-range/Z mixup must not silently change reference geometry: round-trip and analytic ray tests.
- Invalid/sparse or discontinuous reference depth must be rejected before model inference, with a recorded reason.
- Check data must not influence fitted scale: API receipts and explicit one-calibration-only assertions.
- Whole-scene benchmark export must not be described as automatic PV component segmentation.
- A fresh clone must show results without local raw data, and reproduction must explain download/runtime requirements.

### Task 1: Reference data and frozen protocol

**Files:** `services/api/src/pv3d/metric_benchmark.py`, `services/api/tests/test_metric_benchmark.py`, `scripts/public_metric_benchmark.py`, `docs/measurement/public-metric-selection.json`.

**Interfaces:** Reference helper consumes original pixel coordinates, matched depth raster and camera parameters; returns metric XYZ and sampling diagnostics. Runner consumes selection and cached public archives; writes raw local geometry and API receipts plus a compact public summary.

- [x] Test distortion inversion, letterbox pixel mapping, invalid depth and depth discontinuity rejection; observe RED.
- [x] Implement only the required reader/ray/sampling helpers and verify GREEN.
- [x] Download/hash source archives, inspect contact sheets, select two triplets and at least six endpoints per scene based on photograph/reference availability, and freeze selection before inference.
- [x] Record source URL, dataset license, failed Agisoft download and why it cannot yet be used as length truth.

### Task 2: Real inference and API measurement

**Files:** `scripts/public_metric_benchmark.py`, ignored `data/measurement-public/`, tracked `docs/measurement/public-metric-results.json`.

**Interfaces:** VGGT `reconstruct` produces relative point map; normal `export_pointcloud` writes the audit GLB. Existing measurement routes fit one scale and validate held-out lengths without changing it.

- [x] Run selected triplets at 336 and 518 with fixed weights; preserve failures and logs. Avoid overlapping the separate E06 GPU run.
- [x] Measure before calibration as relative units, then one reference-calibrated measurement for each held-out segment; persist immutable receipts, hashes, timing and errors.
- [x] Check exported vertex coordinates against point-map endpoints and verify API length math agrees to float32 tolerance; do not align a shape to GT.
- [x] Generate summary from receipts, list every check and exclusion, and publish the resolution comparison without selecting only the better run.

### Task 3: Web, documentation and delivery

**Files:** `apps/web/src/components/PublicMetricBenchmark.tsx`, its focused test and styles, results JSON asset, paired READMEs, measurement guide, quality report/issues/experiments/verification, screenshot provenance.

**Interfaces:** A read-only trilingual panel consumes the compact checked-in result summary and links to original sources; existing job restore and measurement replay show local geometry when prepared.

- [x] Add a failing UI test for held-out results, reference category and language switching; implement the panel and observe GREEN.
- [x] Save a detailed E07 report with all results, known failures, evidence location, reproduction and next steps; update handoff indexes and both READMEs.
- [x] Run backend/frontend suites, build, lint, manifest checks and real browser verification; capture an authentic UI screenshot.
- [ ] Private GitHub push and clean-clone verification remain; fresh review and material RED/GREEN fixes are complete.
