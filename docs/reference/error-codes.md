# Error codes

Stable codes with a user-facing message key and a recovery action. Use these
across workers, WASM, persistence, and UI so failures are diagnosable and
translatable.

Two namespaces:

- `CF-<AREA>-<NNN>` — app-facing. Shown to users.
- `MF-<AREA>-<NNN>` — core/ABI. Raised by `mesh-forge-core`/`mesh-forge-wasm`;
  the app maps each to a `CF-*` code and message key at the boundary.

Format: `CF-<AREA>-<NNN>` (app) and `MF-<AREA>-<NNN>` (core/ABI). The message
key is `err.<lowercased-code>` (e.g. `err.cf-in-001`).

## App codes (CF)

| Code | Message key | Meaning | User action |
|---|---|---|---|
| CF-IN-001 | `err.cf-in-001` | Unsupported image format | Use PNG/JPEG/TIFF/BMP |
| CF-IN-002 | `err.cf-in-002` | Image too large | Reduce dimensions |
| CF-IN-003 | `err.cf-in-003` | Invalid/corrupt image | Try another file |
| CF-IN-004 | `err.cf-in-004` | Invalid parameter value | Correct the field |
| CF-AR-001 | `err.cf-ar-001` | Archive missing required member | Re-export the project |
| CF-AR-002 | `err.cf-ar-002` | Archive member too large | Use a smaller archive or re-export |
| CF-AR-003 | `err.cf-ar-003` | Archive compression ratio too high | Reject; possible bomb |
| CF-AR-004 | `err.cf-ar-004` | Archive path traversal | Reject; possible attack |
| CF-AR-005 | `err.cf-ar-005` | Blob hash mismatch | Re-export the project |
| CF-VR-001 | `err.cf-vr-001` | Unsupported document version | Open read-only or upgrade |
| CF-VR-002 | `err.cf-vr-002` | Unknown future version | Open read-only |
| CF-VR-003 | `err.cf-vr-003` | Migration failed | Open read-only; report |
| CF-WS-001 | `err.cf-ws-001` | WASM load failed | Reload; check network |
| CF-WS-002 | `err.cf-ws-002` | ABI/version mismatch | Reload; update app |
| CF-WK-001 | `err.cf-wk-001` | Worker crashed | Retry; reload if repeated |
| CF-GL-001 | `err.cf-gl-001` | WebGL context lost | Wait for restore; reload |
| CF-MEM-001 | `err.cf-mem-001` | Out of memory | Lower resolution |
| CF-ST-001 | `err.cf-st-001` | Storage quota exceeded | Export + clear cache |
| CF-ST-002 | `err.cf-st-002` | Storage permission denied | Grant or use download fallback |
| CF-FS-001 | `err.cf-fs-001` | File permission denied/revoked | Re-select the file |
| CF-EX-001 | `err.cf-ex-001` | Export validation failed | Check settings; retry |
| CF-EX-002 | `err.cf-ex-002` | Export cancelled | No action needed; retry if unintended |
| CF-EX-003 | `err.cf-ex-003` | Export out of space | Free space; retry |

## Core/ABI codes (MF)

Raised inside the core; the app maps each to the `CF-*` code in the second
column before display.

| Code | Maps to | Meaning |
|---|---|---|
| MF-BUF-001 | CF-MEM-001 | Buffer allocation failed |
| MF-BUF-002 | CF-IN-004 | Invalid buffer shape/stride |
| MF-ABI-001 | CF-WS-002 | ABI version mismatch |
| MF-ABI-002 | CF-WS-002 | Capability mismatch (missing op/feature) |
| MF-ABI-003 | CF-WS-002 | Invalid handle (freed or stale generation) |
| MF-ABI-004 | CF-IN-004 | Out-of-bounds bulk descriptor |
| MF-ABI-005 | CF-WS-002 | Invalid command encoding |
| MF-TR-001 | CF-WK-001 | Worker terminated |
| MF-TR-002 | CF-WS-002 | RPC envelope malformed |
| MF-TR-003 | CF-EX-002 | Job cancelled |
| MF-PS-001 | CF-AR-001 | Archive missing member |
| MF-PS-002 | CF-AR-002 | Archive member too large |
| MF-PS-003 | CF-AR-003 | Compression ratio too high |
| MF-PS-004 | CF-AR-004 | Path traversal / duplicate entry |
| MF-PS-005 | CF-AR-005 | Blob hash mismatch |
| MF-PS-006 | CF-VR-003 | Migration failed |
| MF-EX-001 | CF-EX-001 | Export validation failed |
| MF-EX-002 | CF-EX-002 | Export cancelled |
| MF-EX-003 | CF-EX-003 | Export sink write failed |

Rules:
- Never show raw stack traces to users; log them, show a code + message.
- Keep codes stable; add, don't rename.
- Every code has a message key and a recovery action.
- Core codes are internal: they cross the ABI as integers or short strings and
  are mapped to CF codes before display.

---

Part of the shared docs. Index: [docs/README.md](../README.md).
