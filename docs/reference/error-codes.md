# Error codes

Stable codes with a user-facing message key and a recovery action. Use these
across workers, WASM, persistence, and UI so failures are diagnosable and
translatable.

Format: `CF-<AREA>-<NNN>`.

| Code | Meaning | User action |
|---|---|---|
| CF-IN-001 | Unsupported image format | Use PNG/JPEG/TIFF/BMP |
| CF-IN-002 | Image too large | Reduce dimensions |
| CF-IN-003 | Invalid/corrupt image | Try another file |
| CF-IN-004 | Invalid parameter value | Correct the field |
| CF-AR-001 | Archive missing required member | Re-export the project |
| CF-AR-002 | Archive member too large | — |
| CF-AR-003 | Archive compression ratio too high | Reject; possible bomb |
| CF-AR-004 | Archive path traversal | Reject; possible attack |
| CF-AR-005 | Blob hash mismatch | Re-export the project |
| CF-VR-001 | Unsupported document version | Open read-only or upgrade |
| CF-VR-002 | Unknown future version | Open read-only |
| CF-VR-003 | Migration failed | Open read-only; report |
| CF-WS-001 | WASM load failed | Reload; check network |
| CF-WS-002 | ABI/version mismatch | Reload; update app |
| CF-WK-001 | Worker crashed | Retry; reload if repeated |
| CF-GL-001 | WebGL context lost | Wait for restore; reload |
| CF-MEM-001 | Out of memory | Lower resolution |
| CF-ST-001 | Storage quota exceeded | Export + clear cache |
| CF-ST-002 | Storage permission denied | Grant or use download fallback |
| CF-FS-001 | File permission denied/revoked | Re-select the file |
| CF-EX-001 | Export validation failed | Check settings; retry |
| CF-EX-002 | Export cancelled | — |
| CF-EX-003 | Export out of space | Free space; retry |

Rules:
- Never show raw stack traces to users; log them, show a code + message.
- Keep codes stable; add, don't rename.
- Every code has a message key for i18n.

---

Part of the web build docs. Index: [docs/README.md](../README.md).
