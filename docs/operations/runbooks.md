# Runbooks

Short, practical recovery steps for the planned web app. Personal scale: these
exist so a failure does not turn into hours of debugging.

## PWA update fails / stale app

1. Check service worker version and cache name.
2. Hard reload; verify the new bundle hash is served.
3. If a bad build shipped, roll back the static deploy to the previous artifact.
4. Ensure the update strategy is "prompt" (not silent) so users are not mid-edit.

## WASM fails to load / instantiate

1. Check the network tab for the `.wasm` response (MIME `application/wasm`).
2. Verify COOP/COEP headers if the shared-memory build is used.
3. Fall back to the scalar/non-shared build if SIMD/atomics are unsupported.
4. Confirm ABI version matches the JS host; show a clear error on mismatch.

## Worker crash

1. Detect via `onerror`/`onmessageerror`; terminate and recreate the worker.
2. Rebuild the job from the last document revision; never resume torn state.
3. If it repeats, capture a diagnostics bundle and suggest a reload.

## GPU context loss

1. Listen for `webglcontextlost`; prevent default, pause the render loop.
2. On `webglcontextrestored`, re-upload textures/buffers from CPU-side state.
3. If restoration fails, show a recoverable message; keep the document intact.

## Storage quota exceeded

1. Catch `QuotaExceededError`; stop autosave, keep the in-memory document.
2. Prompt the user to export the project, then clear cache/orphaned blobs.
3. Offer a lower-resolution export if relevant.

## Migration failure

1. Do not modify the original archive.
2. Show the failing schema/container version and the error code.
3. Offer read-only open or a diagnostic export of `manifest.json`/`document.json`.

## Support bundle

A diagnostics export should include: app version, build hash, browser/OS,
WebGL/WebGPU capabilities, WASM ABI/core/opset versions, feature flags, and
recent error codes — **never** project content or images. Redact by default.

---

Part of the web build docs. Index: [docs/README.md](../README.md).
