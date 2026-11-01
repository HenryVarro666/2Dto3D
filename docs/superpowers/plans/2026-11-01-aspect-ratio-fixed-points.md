# Fixed-point aspect-ratio comparison implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline, then a fresh whole-branch reviewer.

**Goal:** Compare current14-aligned resizing with isotropic resizing, keeping six ETH3D photos, pinned VGGT,518-square inference and20 physical endpoints fixed; diagnose kicker cross-wall and regressions; preserve results, trilingual web and bilingual README; private sync.

**Architecture:** Extend the current RGB preparation with an explicit experimental isotropic mode while leaving default legacy14 byte-identical. Keep PIL bicubic anti-aliased downsampling and518-square white letterbox. A scalar scale with fractional source-box sampling preserves the original aspect exactly; retain integer storage rect separately from the continuous physical content rect. Freeze mappings/tensor hashes before16 model calls. Reuse E08 sampling/audit/API machinery without changing its archived data.

**Tech stack:** Existing Pillow/NumPy/OpenCV, isolated VGGT/MPS, FastAPI/React/Three.js. No new dependencies/model/weights/training.

**Spec:** Current user request; [E08 report](../../quality/2026-11-01-undistortion-fixed-points.md); design below.

## Global constraints and design decisions

- Startcf98129 in existing isolatedworktree; canonical checkout and other chats are untouched. Existing E07/E08 artifacts/protocols remain immutable. Raw outputs under ignoreddata/measurement-resize; same append-only measurement runtime data/measurement-public/runtime.
- VGGT weights860abec7937da0a4c03c41d3c269c366e82abdf9 and codea288dd0f14786c93483e45524328726ab7b1b4ce; all inputs518×518. Model receives RGB only. Calibration and GT rules unchanged. Product default336 and legacy14 preparation unchanged.
- Primary comparison fixes rectified RGB; original RGB is a separate protection stratum. Two scenes×two RGB conditions×two resize modes×two rounds=16 real calls. Repeat reverses run order. Each stratum has8 held-out lengths, not16 independent scenes. Never pool original/rectified into a new claimed sample size.
- legacy14: same prepare_images output,518×350 integer content for6048×4032; sy/sx=525/518. New isotropic: s=518/6048, continuous content518×345.333333, allocated518×346, centeredfractional content offsety86.333333 within518square. Storage floors each left/top and ceils each right/bottom to avoid fractional clipping at other aspect ratios. Source-box PIL resize uses the sameBICUBIC filter with source white padding as needed; no nearest-pixel endpoint snapping. This tests the complete preprocessing policy (active pixel coverage/padding change too), not a perfectly isolated depth-head cause.
- Exact isotropic mapping: grid=(photo+.5)*s + offset - .5. Store mapping_rect continuous and rect integer separately. Independent tests cover half-pixel, non-square/portrait/extreme aspect, scalar scale in both axes, mapping inverse and known-K transform. Legacy input hashes/arrays must equalE08.
- Support masks conservatively erode original valid mask by bicubic footprint using actualscale; inverse affine grid lookup rejects padding, white border and invalid neighbours. No high-error sample exclusion. All20 frozen physicalXYZ/reference arrays retained; every four-neighbour anchor must pass support and mapping checks or case fails visibly.
- Each condition fits scale only withA–B; four held-outs never used to choose/refit it. Primary uses predictedK; knownK auxiliary only rectified, separateA–B fit. Compare C/D depth ordering and G/H depth span; inspect all regressions, not only averages. Input/geometry/anchor/receipt hashes and worker timings retained.
- UI displays resize comparison per fixed RGB condition, clearly labelled current vs isotropic, per-line regressions, mapped sample provenance, known-K depth diagnosis and cloud replay. zh/en/es copy, matching Chinese/English README figures/screenshots and source credits. No claims of physical field precision or tested5080.

## Review focus

- Fractional content versus allocated integer rect: no silent integer cast in mapping/support/K; test source→grid→source and analytic off-axis camera rays.
- Legacy default must be byte-identical and default worker behavior unchanged; test both default/explicitlegacy and real E08 input/arrays.
- Isotropic pixels must use the frozen transform actually executed in isolated worker; actual worker tensor hash must equal protocol. Border filtering must include resampler support.
- Failure evidence always persists and CLI exits nonzero. No unrelated queued jobs interrupted; no browser-supplied XYZ.
- Aggregates compare only matching RGB/resize strata, same protocol/model/GT and exactly4held-outs per scene; missing/mismatched cases withhold aggregate. Locale switch preserves values/job IDs.

### Task1: Preparation, mappings and frozen protocol

**Files:** reconstruction.py,undistortion.py,infer.py; newresize_benchmark.py and tests; measurement/resize-selection.json.
**Interfaces:** image_layout(width,height,target_size=518,resize_mode='legacy14') gives integerrect,continuousmappingrect and isotropicscale; prepare_images(paths,target_size,resize_mode) retains its2return values; VggtReconstructor optionalresize_mode forwarded to worker; new runner uses mapping_rect for E08 math.
- [ ] RED:scalar scales/fractional content/inverse mapping/legacy pixels/invalid mode and footprint. Expected tests fail for missingnewmode; no model execution.
- [ ] Implement minimal optional isotropic mode with PIL floating-box bicubic; testsGREEN. Verify baseline interfaces and all8sourceinput hashes.
- [ ] Freeze8case input hashes, mappings, support and common20physicalpoints/refarrays; builder review settled before inference; commit before any new model call.

### Task2: Controlled real evaluation and diagnostics

**Files:** resize_benchmark.py, compactresize-results/repeat JSON, ignoredarrays/clouds/anchors/receipts/logs.
**Interfaces:** run(args,protocol) verifies frozen tensors, pinnedweights, fixedpoint sampling and measurement readback; allfailed cases persist then nonzero; publisher separate from raw summaries.
- [ ] Use real worker for8conditions; compare legacy arrays and measurement values to E08, fail on divergence. Repeatreverse8conditions.
- [ ] Verify primary/repeat hashes/arrays/lengths; retainallfailed or worse checks, worker/cachetiming scope.
- [ ] Diagnose kickerG–H raw length/depthspan/camera; retainC–Ddepthordering, sidewall andotherregressions. Known-Kaux separately labelled. Do not infer a unique cause from one smallsample.

### Task3: Presentation, durable evidence and private delivery

**Files:** newResizeComparison component/test,workbench/i18n/styles; pairedREADME/figures/screenshots; report/issues/experiments/verification/measurementguide.
**Interfaces:** frozenmatching-stratum data with onRestore(jobID), no extra modelcalls on locale/selection.
- [ ] UI RED/GREEN for stratum switching, same-refguard, complete/worse rows and language/jobID preservation. Productionbuild and browser show real data/diagnostics/replay.
- [ ] Save allissues/failures/improvements, before/aftertable,times/provenance and nextactions. Preserve E08 ashistory. Update12SVG expectedcount if one bilingualchartpair added.
- [ ] Fullbackend/frontend/build/Ruff/figures/links; fresh independent wholebranchreview; fix materialfindingsRED/GREEN.
- [ ] Privatefeature/main sync; freshGitHubclone setup/test/build/preparation and bounded real modelsmoke fromindependent runtime with explicitlycachedsources/weights; recordexactSHAs and keep productionwebavailable.
