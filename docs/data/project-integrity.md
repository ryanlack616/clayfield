# Project integrity and data robustness

Applies to the planned web app; the desktop app already uses atomic save and
recovery snapshots.

## Project format

```
project.zip
  manifest.json        # container version, app id, schema id/version, blobs
  document.json        # app schema (zod-validated)
  blobs/<sha256>.<ext>
```

- Manifest lists every blob with `{id, kind, codec, dtype?, shape?, hash, byteLength}`.
- Verify SHA-256 of each blob on load; reject mismatches.
- Validate document schema; unknown future version opens **read-only** or errors
  clearly.
- Never mutate an old archive in place; write a new one.

## Save / autosave / recovery

- **Atomic save**: write to a temp file/stream, then swap.
- **Autosave** to OPFS at a fixed cadence and on significant edits; keep one
  recovery snapshot.
- On startup, detect an unclean shutdown/recovery snapshot and offer to restore.
- Recovery UI must never silently overwrite a newer file.

## Multi-tab

- Use Web Locks or `BroadcastChannel` to elect one writer per project.
- Other tabs open the project read-only and show a banner.
- On conflict, never last-write-wins silently; ask the user.

## File System Access

- Persist handles in IndexedDB; re-check permission on use.
- Handle denied/revoked permission with a clear re-prompt or OPFS fallback.
- Fall back to `<input type=file>` + download where FSA is unavailable.

## Storage quota

- Call `navigator.storage.persist()` and surface whether it was granted.
- Estimate usage before large writes; warn on low quota.
- Handle `QuotaExceededError` gracefully; suggest export + cleanup.
- Provide "clear cache / orphaned blobs" and warn before deleting projects.

## Blobs

- Content-addressed; deduplicate identical blobs.
- Garbage-collect blobs not referenced by any document or recovery snapshot.
- Never GC while a save/export is in flight.

## Errors

- Stable error codes (see [docs/reference/error-codes.md](../reference/error-codes.md))
  with user-facing messages and recovery actions.
- Distinguish: invalid input, unsupported version, out-of-memory, permission
  denied, storage full, worker/GPU failure, corrupt archive.

## Backup / export

- Allow exporting the project archive independent of autosave.
- Document that clearing site data deletes local projects.

---

Part of the shared docs. Index: [docs/README.md](../README.md).
