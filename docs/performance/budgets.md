# Performance and resource budgets

Targets for the planned web app. Numbers are starting points; tune once real
measurements exist. Desktop-first (Chromium/Edge), with graceful degradation.

## Budgets (desktop)

| Metric | Target | Notes |
|---|---|---|
| JS bundle (gzip) | ≤ 300 KB | Excludes WASM; code-split panels |
| WASM core (gzip) | ≤ 3 MB | SIMD build; keep domain out of core |
| First load (LCP, cold) | ≤ 2.5 s | Static host + cached assets |
| Time to interactive | ≤ 4 s | After first visit, near-instant |
| Viewport frame time | ≤ 16 ms @ 512² | 60 fps; single mesh |
| Sculpt dab latency (p95) | ≤ 33 ms @ 2048² | ≥ 30 Hz; dirty-rect updates |
| PROCESS re-eval | ≤ 100 ms typical | Debounced; cached stages |
| Height mapping (2048²) | ≤ 500 ms | Rust/WASM SIMD |
| Export (STL 1024²) | ≤ 5 s | Streamed |
| Export (STL 2048²) | ≤ 30 s | Warn; ~hundreds of MB |
| Peak memory (2048²) | ≤ 1.5 GB | Preflight; reject if over |
| Storage per project | Warn > 100 MB | Blob dedup; GC orphans |

## Rules

- **Preflight before allocating**: estimate buffers and reject with a clear
  message if over the cap (2048² authoritative).
- **Stream exports** to an `ExportSink`/Blob; never assemble the whole file in memory
  when avoidable.
- **Dirty-rect texture uploads** during sculpt; avoid full re-upload.
- **Backpressure**: one in-flight job per worker kind; coalesce pointer events to
  one request per animation frame.
- **Unified memory budget** across JS + WASM + GPU; track and display in a
  diagnostics panel.
- **OOM policy**: fail gracefully, cancel the job, keep the document intact,
  suggest a lower resolution.
- **Resource cleanup**: revoke `ImageBitmap`/object URLs, dispose GL resources,
  terminate/recreate workers, remove listeners.
- **Context loss**: show a recoverable message; re-upload resources on restore.

## Measurement

- Lighthouse CI for load metrics.
- `size-limit` for JS/WASM budgets.
- Rust `criterion` benches for hot ops.
- Playwright performance traces for frame/sculpt timing.
- Memory harness for peak usage at 1024²/2048².
- Store baselines; fail CI on regressions beyond a threshold (start as warnings).

## Mobile

Expect lower caps (likely 1024², tighter memory). Detect device class and reduce
defaults; never assume desktop memory.

---

Part of the shared docs. Index: [docs/README.md](../README.md).
