# V1 Restore Procedure

The V1 archive is:

```text
clayfield-v1.7z
SHA-256: bdf4f23dca1d768f876143d8f0bf4b1e8415cbde3ef94d977a3e8b7d9f2c1f37
```

The archive was integrity-tested with `py7zr` and contains 22,596 entries.

## Restore

1. Verify the checksum:

   ```sh
   sha256sum clayfield-v1.7z
   ```

2. Create a clean restore directory outside the active checkout.
3. Extract the archive with a 7-Zip-compatible tool:

   ```sh
   7z x clayfield-v1.7z -o/path/to/clayfield-v1-restore
   ```

4. Create a fresh Python environment in the restored project.
5. Install the project with its test dependencies.
6. Run the baseline suite:

   ```sh
   .venv/bin/python -m pytest -q
   ```

7. Confirm the expected V1 baseline is approximately `111 passed, 7 skipped`
   on the original supported environment.

Do not restore over the active V2 checkout. The archive is a rollback/reference
copy, not an in-place migration mechanism.

---

Part of the project docs. Index: [README.md](README.md).
