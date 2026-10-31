# Project guidance

## Current state

This repository contains V2 of the Phase 1 local web workbench: React/Three.js, FastAPI, real Grounding DINO/SAM2, guided box/positive/negative-point refinement, explicit single/multiple detection scope, SQLite jobs/refinements and Trimesh schematic GLB. Read README.md and docs/running.md for commands, docs/v2/model-options.md for checkpoint choices. V1 is immutable tag v1.0.0. High-fidelity generative geometry and additional equipment types remain future work. Local photos, weights and results are ignored.

Use `docs/plan.md` for the approved design and docs/implementation-phase1.md for this implementation slice. Research notes retain earlier exploration and are not evidence of implemented behavior. Current behavior must be checked against code and actual tests.

## Confirmed requirements

- Use one photo first; request extra captured views only when needed.
- The user accepts processing longer than 10 seconds. Show actual processing stages and elapsed time; do not invent time-based percentages or time remaining. Optimize latency and report cold/warm end-to-end time, including upload, processing, delivery, and viewer loading.
- The user accepts simplified boxes, rods, and bases first, with background geometry refinement later.
- Phase 1 is confirmed as string inverters and their external mounting structures. Document later expansion to compact substations, transformers, and other equipment; do not silently make all categories part of Phase 1.
- The user has an NVIDIA RTX 5080; the fallback is an M4 Pro MacBook Pro. This execution host is M4 Pro with 24GB memory and MPS available; actual model calls ran here. RTX 5080 OS/driver/available VRAM and performance remain unverified. Use `docs/hardware.md` for resource-aware planning.
- Make visible component composition understandable through selection, hiding, and an explanatory exploded view.
- Support Chinese, English and Spanish UI switching with a remembered local preference. Switching language must preserve active jobs, photos, camera, selection, visibility and user edits; translate built-in labels for display without rewriting API data or user-entered names.
- The canonical local project root is `/Users/caochao/Documents/2Dto3D/`. Earlier ChatGPT and Work paths are obsolete.

## Geometry and evidence

- Keep stable component IDs across input masks, geometry, scene nodes, and manual corrections.
- Refinements are immutable server records. Validate image and bbox ownership before a manual job; never trust client mask polygons or model provenance. Keep complete binary PNGs for disconnected regions/holes, even when JSON contours are simplified.
- Preserve drafts on model errors, coalesce point edits behind one browser request, reject stale responses and retain explicit box-only fallback. Scope selection must not itself launch a job. Both task types share the bounded single inference executor.
- Default SAM remains tiny; optional larger pinned presets are unbenchmarked. Segmentation changes visible boundaries, while current schematic geometry uses bbox/category priors. Do not imply pixel masks produce accurate 3D geometry.
- Distinguish visible components from physical manufacturing parts. Holes, slots, and folds are features unless evidence identifies a separate part.
- Label schematic geometry and inferred hidden surfaces explicitly. Unknown metric scale must not be displayed as measured dimensions.
- A full-object mesh does not demonstrate real component decomposition. Preserve scene hierarchy and verify GLB reload and picking.
- Store original transforms separately from exploded-view display offsets. An exploded view is not a verified disassembly procedure.
- Do not turn VLM suggestions into confirmed labels, exact SKUs, or a complete engineering BOM.

## Data and development

- Keep raw photos, local annotations, weights, intermediate outputs, and generated artifacts in ignored local directories. Do not force-add them to Git.
- The existing two candidate images are local planning references with unverified provenance. Their filenames do not verify product model or common physical identity.
- Store input hashes, model/checkpoint/config versions, scale basis, and per-field evidence with future results.
- Begin with a small no-training baseline. Keep model-specific dependencies isolated from the web/API environment.
- On the standard 16GB RTX 5080, prioritize the perception and schematic path; test a lower-memory shape-only model separately. SAM 3D Objects and TRELLIS.2 exceed its standard VRAM under their official requirements and are conditional higher-memory candidates, not the default local baseline.
- Keep equipment-specific labels and primitive mappings in profiles; share component contracts and the viewer. Use `docs/roadmap.md` to track expansion and category regression checks.
- Report cold and warm latency separately. Record total component completion time as well as the first schematic result.
- Do not invent accuracy, speed, or geometry measurements. Tests and evaluation should establish observable behavior.

The repository is private by default. No external communication or raw-data publication is implied by maintaining this repository.
