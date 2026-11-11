# Threat model

Lightweight STRIDE-style model for the planned web app. Desktop is local and
covered by the same untrusted-input assumptions.

## Assets

- User images and `.clayfield` projects (confidential to the user).
- Exported models (STL/3MF/PNG/TIFF).
- The user's browser storage (OPFS/IndexedDB/File System Access handles).
- Reputation/integrity of the app and its hosted assets.

## Actors / trust boundaries

- **User** (trusted locally).
- **Untrusted input**: project archives, images, filenames, worker messages,
  pasted data.
- **Static host / CDN** (trusted only if HTTPS + integrity controls hold).
- **Third-party dependencies** (untrusted supply chain until vetted).
- **Other tabs** (cooperating but can race on shared storage).

## Threats and mitigations

| Threat | Example | Mitigation |
|---|---|---|
| Tampering | Malicious `.clayfield` archive, zip-slip paths, oversized members | Strict member allowlist, size/ratio limits, reject absolute/`..` paths, no execution of archive content |
| DoS | Decompression bomb, huge image dimensions, huge JSON, runaway worker | Decode/size budgets, max dimensions, reject non-finite/zero, cancellation, worker terminate |
| Spoofing | Malicious CDN asset or stale service worker | HTTPS/HSTS, SRI for remote assets, pinned deps, CSP, cache versioning |
| Info disclosure | Telemetry leaking project content | No telemetry by default; opt-in crash reports redact content |
| Elevation | WASM memory bug or unsafe Rust | Minimize `unsafe`, `cargo-geiger`, fuzzing, bounds checks, WASM sandbox |
| Injection | Worker message / JSON injection | Typed schema validation (zod), size limits, never `eval` |
| Repudiation | n/a (no accounts) | — |
| Cross-tab races | Two tabs saving the same project | Web Locks/BroadcastChannel; read-only second tab |

## Web security headers (host-provided)

```
Content-Security-Policy: default-src 'self'; script-src 'self' 'wasm-unsafe-eval';
  style-src 'self' 'unsafe-inline'; img-src 'self' blob: data:; worker-src 'self' blob:;
  connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'
Cross-Origin-Opener-Policy: same-origin
Cross-Origin-Embedder-Policy: require-corp
Cross-Origin-Resource-Policy: same-origin
Strict-Transport-Security: max-age=63072000; includeSubDomains
Permissions-Policy: camera=(), microphone=(), geolocation=()
```

Notes:
- `wasm-unsafe-eval` is required to compile WebAssembly; scope it tightly.
- COOP/COEP are required for `SharedArrayBuffer`; keep the transferable fallback
  when they are unavailable (e.g., hosts that cannot set headers).
- Consider Trusted Types once DOM sinks are audited.
- No `unsafe-inline` scripts; avoid inline event handlers.

## Input validation requirements

- Images: allowed extensions/MIME + magic-byte check, max dimensions, max bytes,
  reject zero/NaN.
- Archives: max members (e.g., 32), max total uncompressed, max member size,
  compression-ratio cap, reject path traversal and duplicate entries.
- JSON/document: schema validation, size caps, op-param range checks.
- Worker messages: typed envelopes, size caps, generation/cancel validation.

## Fuzzing targets (when web work starts)

- Archive parser, image decoder handoff, worker message decoder, ABI command
  decoder, persistence schema validator.

## Supply chain

- Commit lockfiles; pin toolchains.
- `cargo audit`/`cargo deny`, `npm audit`/dependency review, secrets scanning.
- SBOM before public release; review new dependencies for license and activity.

---

Part of the web build docs. Index: [docs/README.md](../README.md).
