# ClayField V2 Acceptance Report

Status: release candidate locally packaged; external validation remains open

## Local Verification

- V1 baseline: `111 passed, 7 skipped`.
- Current V2 suite: `179 passed, 7 skipped`.
- Application self-test: passed.
- Clean temporary wheel installation/import: passed.
- V2.0.0 wheel build: passed.
- V2.0.0 PyInstaller bundle build: passed.
- Packaged `--self-test`: passed.
- Packaged `--gl-self-test`: passed on NVIDIA OpenGL 3.3.
- Packaged `--version`: reports `ClayField 2.0.0`.
- Release SHA-256 manifest verification: passed.
- Release archive: `dist/clayfield-2.0.0-linux-x86_64.tar.gz` generated with
  SHA-256 `b27ab5ccc66cf6fe0fc1bdcc4e4bb1701284234d8e7300f39d0a7b249ac4c131`.
- 1024 x 1024 mesh benchmark completed.
- Full 1024² validation observed approximately 3.5 GiB peak RSS; export safety
  now uses a conservative 20x working-set estimate.
- Image-primary and procedural-primary composition coverage: passed.
- External field persistence and provenance coverage: passed.
- External heightmap and mask import coverage: passed.
- GPU/CPU agreement test on the available OpenGL environment: passed.
- Stress tests: passed.
- Local native, composed, and imported STL checks: passed.
- Final export-resolution analysis coverage: passed.
- Deterministic V2 sample projects and artifacts: generated locally with
  `benchmarks/v2_samples.py`.
- Fabrication calibration panel generator: available through
  `benchmarks/fabrication_calibration.py`; physical inspection remains open.

## External Validation Required

These checks are not available in the current environment and remain open:

- Verify `clayfield-v1.7z` contents with a 7-Zip-compatible tool.
- Test clean-machine restore from the V1 archive.
- Run PrusaSlicer STL/3MF QA with `CLAYFIELD_PRUSA_SLICER` configured.
- Test additional Ubuntu versions and GPU drivers.
- Perform physical print and calibration validation.

## Release Policy

The planned V2 product release is `2.0.0`. Local artifacts are built, but it
must not be released until all
P0 blockers are closed and every unavailable external validation item is either
completed or explicitly accepted as a documented release exception.

The daily execution board is
[`V2-MASTER-TASK-LIST.md`](../V2-MASTER-TASK-LIST.md). The full specification and
release-blocker register are in
[`V2-MASTER-PLAN.md`](../V2-MASTER-PLAN.md).
