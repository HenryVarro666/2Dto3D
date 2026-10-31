# V3 Multiview Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline, then one fresh whole-branch review. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver multi-angle photo groups, real fused component point clouds and per-view manual corrections while preserving V2.

**Architecture:** Add capture/job contracts and tables alongside the existing single-image API. Run pinned VGGT in an isolated subprocess environment on the same bounded worker; retain geometry for manual reassignment, export pickable point-cloud GLB/PLY and use the existing photo/editor/viewer interactions.

**Tech Stack:** FastAPI/Pydantic/SQLite, NumPy/OpenCV/Trimesh, isolated PyTorch/VGGT, React/TypeScript/Three.js.

**Spec:** `docs/superpowers/specs/2026-10-31-v3-multiview.md`.

## Global Constraints

- Canonical root `/Users/caochao/Documents/2Dto3D/`; worktree `.worktrees/v3-multiview`, branch `feat/v3-multiview`, base `ae4816c`.
- Preserve old single-image APIs, images/database and V2 behavior; do not interrupt canonical V2 until V3 is verified.
- Use one shared bounded inference worker; keep photos, weights and generated data ignored/local.
- Support 2–8 unique photos; record unknown metric scale and inferred associations explicitly. No fabricated geometry or real-dimension claims.
- Keep Chinese/English/Spanish, stable IDs and explicit confirmation/fallback; no stale response may overwrite edits.

## Review Focus

- Letterboxing and source/model pixel conversion must not attach points from a neighboring part or padding.
- Manual jobs must not consume geometry/refinement records from another capture/image, or lose unchanged evidence.
- Image changes/cancellation/mode or language switches must not allow late jobs to replace a newer workspace.
- Missing models, empty/invalid geometry, queue saturation or subprocess failure must retain actionable state without pretending success.
- Same-category adjacent objects must not silently merge within the same photo; explicit association edits preserve identity and remain reversible through versioned jobs.

---

### Task 1: Capture contracts, durable jobs and shared queue

**Files:** new `services/api/src/pv3d/captures.py`, `multiview_schemas.py`; modify `store.py`, `app.py`; new `tests/test_multiview_api.py`.

**Interfaces:** `CaptureCreate(asset_ids:list[str],2..8)`; `Capture{id,assets,created_at}`. `MultiJobRequest{capture_id,mode:'automatic'|'manual',observations?:ViewInput[],base_job_id?}`; `ViewInput=ManualComponent+{id,asset_id,component_id?}`. `MultiJob{id,capture_id,status,stage,view_index,total_views,created_at,elapsed_ms,error,result}`. `MultiResult{job_id,capture_id,geometry_job_id,representation:'fused_point_cloud',metric_scale_status:'unknown',views,observations,components,scene_url,ply_url,json_url,point_count,context_point_count,model,quality,timings,warnings}`.

- [ ] Write tests for group size, unknown/duplicate photos and content hashes, invalid mode, durability/restart interruption, cross-capture manual base and refinement ownership, shared queue capacity. Run targeted tests and witness missing endpoint/contracts failures.
- [ ] Implement additive tables and resource checks, `/api/captures` POST/GET and `/api/multiview/jobs` POST/GET/artifact endpoints; integrate runner injection into `create_app(...,reconstructor=None)` and reuse its executor/capacity.
- [ ] Supply actual stage/view counts and sanitized failure paths. Manual evidence resolution is shared with V2, preserving existing behavior.
- [ ] Run backend suite; expected all core tests pass without model downloads. Commit.

### Task 2: Pinned VGGT worker and image geometry

**Files:** new `services/multiview/{pyproject.toml,uv.lock,infer.py}`, new `services/api/src/pv3d/reconstruction.py`; new tests `test_reconstruction.py`; Makefile targets.

**Interfaces:** `VggtReconstructor.reconstruct(image_paths:list[Path],output_dir:Path,on_progress)->dict` writes `geometry.npz` with points `[S,H,W,3]`, depth/confidence `[S,H,W]`, colors `[S,H,W,3]`, per-image `rects:[left,top,right,bottom]`, extrinsics/intrinsics. Metadata includes checkpoint/revisions/device/input size/timings. Worker stdout lines are bounded JSON stage records, errors stay in local logs.

- [ ] Test aspect-ratio-preserving pad transforms, normalized photo-to-grid mappings, invalid arrays/shapes and subprocess failures before implementation; witness RED.
- [ ] Use official VGGT source commit `a288dd0f14786c93483e45524328726ab7b1b4ce`; discover/fix weight revision. Install isolated NumPy 1.x environment, lazy load safetensors, disable unused point/track heads and use depth+camera unprojection in one world frame.
- [ ] Add model-preparation command and local ignored caches, document research checkpoint license. Run core tests and a real official same-scene sample on available hardware; capture real arrays/poses and stage times without accuracy claims. Commit.

### Task 3: Semantic point fusion, associations and artifacts

**Files:** new `services/api/src/pv3d/pointcloud.py`, `multiview_runner.py`; tests `test_pointcloud.py`, expand API tests.

**Interfaces:** `build_pointcloud(geometry,assets,observations,store,automatic:bool)->dict` returns authoritative observations/components, filtered vertex/color/component arrays and quality diagnostics. `export_pointcloud(...,folder)` emits GLB with POINTS nodes/extras and PLY with component index plus JSON ID mapping. Source geometry is immutable and reused via validated base result.

- [ ] RED tests for letterbox exclusion, finite/depth/confidence filtering, RGB and Y-up conversion, voxel averaging across views, mask holes and multiple islands, distinct adjacent components, stable IDs/manual link and split, PNG ownership and geometry reuse without reconstructor call.
- [ ] Detect components per view, map masks to shared geometry, suggest same-category cross-view associations only when spatial support agrees and no same-view conflict. Persist versioned observations; apply explicit manual grouping/name/category changes and retain unknown/background points separately.
- [ ] Filter and voxel-merge, cap exported cloud at 150,000 points deterministically, record cross-view support/low-parallax diagnostics. No valid points means needs review, not a fake cloud. Serialize finite JSON only.
- [ ] Verify GLB reload, node IDs and PLY metadata; run backend suite, commit.

### Task 4: Three-language multiview workspace and point rendering

**Files:** new `apps/web/src/{core/multiview.ts,components/MultiviewWorkbench.tsx}` and tests; API types/client/fixtures, App, PhotoPanel, SceneViewer/sceneState, messages/styles.

**Interfaces:** `WorkbenchApi.createCapture/getCapture/createMultiJob/getMultiJob`; `useMultiview(api)` owns generation-guarded upload/create/poll/manual rebuild. Single and multiview workspaces remain mounted after use, mode changes disabled during tasks/drafts. Per-view observation edits feed `MultiJobRequest`; only server refinement references submitted.

- [ ] RED tests: 2–8 photo selection/removal, upload/poll/cancel/late response, switching view maintains edits, guided confirmation on the correct photo, language preserves active group, manual link/split/rename/category behavior and single-mode regression.
- [ ] Implement photo strip, explicit fusion start, real stage/view progress, global component list and editable current-view observations; preserve V2 annotation controls and per-view coordinate identity.
- [ ] Extend GLB viewer/scene state for native Three.js Points, selection/hidden/background/isolation, point size and proper disposal; no point-cloud wireframe claim. Keep scene picking IDs and exported original transforms.
- [ ] Run frontend suite/build and backend suite; commit.

### Task 5: Browser verification, documentation and V3 release

**Files:** README/AGENTS/CHANGELOG/running/API/i18n/verification/roadmap, new `docs/v3/` capture guide and model notes; version metadata.

- [ ] Real API and browser on isolated data/port: upload actual distinct official multiview images, visualize real fused points, pick/hide/background, per-view annotation and manual geometry reuse, downloads and three languages; save ignored evidence. Do not pass unrelated photovoltaic photos as a valid pair.
- [ ] Document capture instructions, 336 resolution limits, research checkpoint and isolated env, real measured run conditions, untested 5080/domain accuracy and relative scale.
- [ ] Run complete tests/build/Ruff/diff checks; request one fresh whole-branch review on the most capable model, reproduce/fix Important findings with RED→GREEN and rerun full suite.
- [ ] Set 3.0.0 metadata, merge verified work into canonical root, preserve saved V2 data, push main/tag/release `v3.0.0`, verify CI and open the running V3 page. Existing V1/V2 tags remain unchanged.
