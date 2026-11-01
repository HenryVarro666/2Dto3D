# Independent real scenes implementation plan

Use superpowers:executing-plans inline with TDD and fresh whole-branch review. Spec: [design](../specs/2026-11-01-independent-real-scenes-design.md). Baseline66fd7cc; branch eval/independent-real-scenes in existing isolated measurement worktree.

## Global constraints

Follow design, fixed VGGT518/physical anchors, four policies, scan-only reference, no changed defaults or old results. E10-M avoids concurrent E10 component-recognition work. All raw data under ignored data/measurement-independent; append jobs to existing measurement runtime. Freeze protocol in Git before actual model inference.

## Review focus

No selection from prediction errors; exact physical endpoint mappings; scanGT never model input; all12 held-outs and failure cases; matching strata and reference arrays; source/weights independence limits; preserve E09/defaults/concurrent work and private packaging.

### Task 1: Sources and frozen protocol

Files: new independent_benchmark.py/source selection/protocol and API tests; minimal parameterization of resize_benchmark.py. Interfaces: new selection supplies scene camera, views, ten scan points and five segments; new preparation emits E09-compatible cases with frozen tensor/support hashes; shared runner accepts explicit protocol/config/experiment and optional prior archive.

- Download official archives; select overlapping views and scan-supported physical endpoints; retain failed reference candidates. Verify scene/hash disjointness from E07–E09.
- RED/GREEN for overlap rejection, GT selection/mapping, input tampering and independent runner avoiding E09 comparison. Test existing E09 behavior.
- Freeze all12case inputs and physical references in committed protocol before calls.
- Validation: .venv/bin/python -m pytest services/api/tests/test_independent_benchmark.py services/api/tests/test_resize_runner.py services/api/tests/test_metric_benchmark.py services/api/tests/test_undistortion.py services/api/tests/test_aspect_resize.py -q

### Task 2: Real evaluation and evidence

Files: independent runner/publisher; compact results/repeat; quality report. Interfaces: Task1 frozen cases ->24 actual calls -> verified per-case results/repeat, known-K diagnostics and persistent measurement receipts. Preserve every run/failure.

- Primary12calls and reversed12repeat, cached pinned worker sequential MPS.
- Verify input/arrays/clouds/reference/measurements; calculate all four policy statistics, cross-wall subset and individual regressions; no claimed fix from averages.
- Validation: .venv/bin/python scripts/publish_independent.py --check

### Task 3: Web, docs and private release

Files: independent-scene component/tests, workbench/i18n/styles; pairedREADME and generated figures/screenshots; issues/experiments/verification/guides. Interfaces: Task2 complete immutable results -> four-policy panel with source gallery and real replay, no model calls from UI selections.

- RED/GREEN panel shows all12 lengths and missing-data guard; preserves locale values and restore callbacks; real browser screenshots/replay.
- Save results/problems/improvements/timing/limits; pairedREADME and credited images. Full tests/build/Ruff/figures. Final review follows Task3 completion as required by executing-plans.
- Private feature push; fresh clone setup, frozen preparation and bounded actual model smoke with caches explicitly disclosed. Keep live workbench.
- Validation: make test && make build && .venv/bin/python scripts/readme_figures.py --check

## Final review and release gate

After Task3 implementation/checks, dispatch the required fresh whole-branch reviewer; fix material findings RED/GREEN, preserve all evidence. Only then fetch and integrate any concurrent main changes, repeat affected verification, atomically push feature/main without force and verify exact remote SHA/CI. This orders the already authorized delivery after the required review instead of placing review inside its own completion prerequisite.
