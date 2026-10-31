# Project guidance

## Current state

This is a planning repository for photo-based PV equipment structure visualization. The initial repository contains a project plan and cited research; the local working directory also contains ignored photos and their metadata index. Application code, model inference, and runtime benchmarks have not been implemented.

Use `docs/plan.md` for the current design. Research notes retain earlier exploration and are not evidence of implemented behavior. The user originally planned to scaffold application code after discussing the design; follow the current request when implementation begins.

## Confirmed requirements

- Use one photo first; request extra captured views only when needed.
- Target a first rotatable schematic 3D result within 10 seconds of submission. This includes upload, processing, delivery, and viewer loading. It is a target, not a measured capability.
- The user accepts simplified boxes, rods, and bases first, with background geometry refinement later.
- Phase 1 is confirmed as string inverters and their external mounting structures. Document later expansion to compact substations, transformers, and other equipment; do not silently make all categories part of Phase 1.
- The user has an NVIDIA RTX 5080; the fallback is an M4 Pro MacBook Pro. Use `docs/hardware.md` for resource-aware planning. Operating system, driver, actual available VRAM, and Mac memory remain unverified.
- Make visible component composition understandable through selection, hiding, and an explanatory exploded view.
- The canonical local project root is `/Users/caochao/Documents/2Dto3D/`. Earlier ChatGPT and Work paths are obsolete.

## Geometry and evidence

- Keep stable component IDs across input masks, geometry, scene nodes, and manual corrections.
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
