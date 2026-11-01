# E08 undistortion comparison with fixed physical points

> **For agentic workers:** Use superpowers:executing-plans inline and a fresh whole-branch reviewer. The user explicitly requested execution and private GitHub sync; preserve this authorization.

**Goal:** Compare the same six ETH3D photographs before/after calibrated undistortion at518px, with identical physical reference endpoints, and explain the two large/regressed kicker checks.

**Architecture:** Freeze E07's20 scanner-derived518 endpoint coordinates. Project each to the original THIN_PRISM_FISHEYE photo and a full-field pinhole rectification. Sample predicted camera-Z bilinearly at the corresponding fractional model-grid pixel, then unproject with each prediction's camera. Preserve raw model arrays/clouds; export a clearly identified derived-anchor layer for the normal immutable measurement API. One length fits scale; four lengths only check it.

**Tech stack:** Existing NumPy/SciPy/OpenCV/Pillow/Trimesh/FastAPI/React. Pinned VGGT worker and cached weights. No new model or training.

**Spec:** Current user request and [E07 measurement evidence](../../quality/2026-11-01-public-metric-measurement.md).

## Global constraints

- Baseline8253f36; isolated existing worktree on`eval/undistortion-fixed-points`; leave canonical E06 source branch untouched.
- Both conditions use VGGT1B revision860abec7937da0a4c03c41d3c269c366e82abdf9, codea288dd0f14786c93483e45524328726ab7b1b4ce,518×518 model input and the same three views/order per scene. Default product resolution remains336.
- Fixed endpoints are E07's518`xyz_m`/`sample_pixel_xy`; they never move to a neighbouring output pixel. GT lengths must be byte-identical between conditions; mapping round-trip <1e-6 original pixel.
- Camera calibration alone constructs rectification. Depth/length truth does not enter image warp or inference. Model receives RGB only; known camera calibration is additional preprocessing information and may not exist for arbitrary user photos.
- Rectify at original6048×4032 size, preserve sampled source-boundary rays with a conservative margin, no fitted crop, white invalid border. Record newK, mapping, invalid fraction, image/pixel/tensor hashes, timing and endpoint coverage.
- Input RGB is kept lossless after decoding; verify the original condition's prepared tensor is identical to E07. JPEG viewer previews are separate, explicitly documented, and never used as model input.
- Bilinear depth sampling estimates model geometry at fixed image positions; it is not a raw model vertex or a sensor measurement. Preserve four neighbours/weights, predicted camera, depth spread and derived XYZ in audit JSON. Nonfinite/outside support fails the case; high error or a predicted depth jump is retained with diagnostics.
- Raw model point maps and raw relative clouds stay unchanged. A separate derived-anchor component in the audit GLB enables vertex-index API receipts. Do not describe view/anchor groups as PV segmentation.
-8 real calls:2scenes×2conditions×2 rounds, reverse condition order on repeat. Freeze protocol before inference and preserve all failures/regressions. Do not inflate independent sample counts with repeats.
- Evaluate an auxiliary known-pinhole-K ray calculation only for rectified images, from the same predicted depths, as labelled diagnosis; it is not the primary before/after metric or a replacement for measured truth.
- Canonical ignored data: data/measurement-undistortion; shared read-only benchmark replay runtime remains data/measurement-public/runtime. Evaluation must not start a job executor or interrupt unrelated jobs.
- Paired Chinese/English READMEs, zh/en/es web copy, issue/experiment/verification handoff, provenance screenshots and private GitHub main/feature sync are required. Raw images/arrays/weights/DB stay ignored.

## Review focus

- COLMAP corner coordinates vs raster-centre/OpenCV coordinates and letterbox mapping must round-trip.
- Fixed physical points and GT lengths must be identical before/after; no silent nearest-pixel snapping.
- Derived anchors must retain full neighbour/camera provenance, and API readback must match float32 export; raw clouds remain available.
- A/B alone fits scale; neither held-out checks nor camera-K diagnostics refit the primary result.
- Rectification field-of-view/borders, resampling changes, failed samples and unknown field precision must remain visible in results and claims.

### Task1: Geometry controls and frozen protocol

**Files:**`services/api/src/pv3d/undistortion.py`, its tests;`scripts/undistortion_benchmark.py`;`docs/measurement/undistortion-selection.json`.

**Interfaces:**camera projector accepts(...,2) normalized rays; rectification returns pinholeK/remap; fixed-endpoint sampler returns neighbour/weight/Z/camera/world-point diagnostics.

- [x] Add RED tests:vector projector matches scalar; full-field boundary and inverse map; noninteger depth-plane sampling and extrinsic transforms; missing/letterbox support rejection.
- [x] Implement minimal functions, verify GREEN; freeze image preprocessing and all20 fixed GT endpoints before inference.
- [x] Save source/input/weights/protocol hashes and mapping residuals; preserve original RGB/tensor equivalence and corrected-image coverage diagnostics.

### Task2: Real controlled evaluation and hard-case analysis

**Files:**existing E07 seed/evaluate helpers receive optional derived anchors and a measurement-only app; focused API test; new runner; tracked compact results and ignored raw evidence.

- [x] RED/GREEN:eval must not mark an unrelated queued job interrupted; API receipts use derived component indices/positions while preserving raw cloud.
- [x] Run original/rectified518 on both scenes, repeat in reverse order; use the sameGT reference lengths, same weights and pixel positions defined by projection.
- [x] Persist raw clouds, anchor audits, GLB/PLY/receipts, timing and all checks. Compare E08 original baseline against E07 without conflating nearest-vertex and subpixel measurements.
- [x] Diagnose kickerC–D andG–H using raw length ratios, predicted camera and calibrated camera-Z residuals; report the known-K auxiliary result separately.

### Task3: Web, documentation and delivery

**Files:**trilingual read-only comparison panel/test/styles, compact JSON asset, paired READMEs/figures/screenshots, measurement guide, E08 report/issues/experiments/verification.

- [ ] UI RED/GREEN for same-reference table, worse/better results and locale preservation; enable immutable audit replay without changing default production calibration.
- [ ] Record complete primary and repeat results, failed hypotheses, assumptions and next actions; update history append-only.
- [ ] Run relevant full suites/build/Ruff/figure and link checks; real-browser verify controls, both views, source/derived distinction, receipts and language switching.
- [ ] Fresh independent review, fix material findings with RED/GREEN; private push, clean-clone verification, final remote-SHA check. Preserve all raw evidence and user-owned E06 branch.
