# Known-length calibration and two-point measurement

User approved implementation on 2026-10-31. The canonical product is `/Users/caochao/Documents/2Dto3D`; this feature is isolated from concurrent V3 quality fixes on `feat/scale-measurement`.

## Scope and evidence

- Measure visible points from a completed multi-view GLB, including old results. Single-photo schematic geometry is ineligible.
- Uncalibrated distances are model estimates in relative units. A reference of known length establishes one global scale. Calibrated lengths retain estimated geometry; they are not certified field dimensions.
- A validation length is supplied independently, never used to fit the scale. Reject the reference segment, reversed or geometrically coincident, as a held-out check. Sharing one endpoint is allowed, but independence of the real measurement/source requires human confirmation.
- No field-measured dimensions are currently available. An authored analytic fixture verifies arithmetic, persistence, UI and deliberately distorted geometry; it does not measure VGGT or field accuracy.

## Contracts and implementation

Point identity is `(component_id, point_index)` in the immutable exported GLB. The service resolves coordinates from that asset and binds every record to job ID, geometry source ID and SHA256. Client coordinates are never accepted. Scene offsets, exploded layouts and camera transforms cannot affect measurements. A modified GLB invalidates existing records. Regenerated jobs require a new calibration even if their source geometry is reused.

Add read-only session/export, immutable calibration creation and measurement creation routes. SQLite stores receipts (endpoints, raw coordinates, units, source note, scale, prediction, independent reference, absolute/relative error, timestamps). Keep original GLB/PLY and result scale status unchanged; calibrated dimensions live in a separate measurement receipt. Download and reopen by job ID; receipts survive service restart.

Viewer point mode uses actual point indices, highlights A/B and the straight segment. Entering point mode resets/disables explosion. Restoring ordinary selection preserves camera. Only visible point-cloud nodes are pickable. Inputs and errors are translated Chinese/English/Spanish; user notes and IDs stay original. Abort/ignore stale requests when jobs change. One operation at a time.

README.md (Chinese) and README.en.md (English) share claims and navigation: real UI captures, a workflow diagram, an architecture diagram, scale/held-out illustration, reproducible model-free demo, full model quickstart, evidence and limits. Only authored analytic demo screenshots and diagrams are committed; raw field photos/results remain ignored.

## Acceptance

Behavior tests: units and 3-4-5 distances; zero/non-finite/unknown points; wrong geometry/job calibration; reversed reference leakage; scale-only correction leaves anisotropic error; immutable persistence/restart/export; old GLB compatibility. UI tests: pick flow, calibrated/uncalibrated states, rejected validation, languages preserve data, stale response and job reset, original-coordinate picking and explosion. Real browser: analytic demo → pick A/B → reference → held-out error → language switch → reload; save authentic screenshots. Full frontend/backend/lint/build and fresh clone reproduction before private push.
