# Security Policy

ClayField runs locally. The desktop app reads local images and writes local
files; it does not send project data anywhere. The planned web app is
client-side only (no server) and stores data in the browser.

## Reporting a vulnerability

This is a personal project. If you find a security issue, please open a private
report (e.g., a GitHub security advisory once the repo is hosted there) rather
than a public issue. If no private channel is available, contact the maintainer
directly.

Please include: affected version/commit, a description, and a minimal reproducer
if possible. Do not include secrets or personal data in reports.

## Supported versions

Only the latest release is supported.

## Scope notes

- **Local-only by design:** no telemetry, no analytics, no remote uploads.
- **Untrusted input:** project archives (`.clayfield`), images, and the planned
  web app's ZIP/image/worker inputs are treated as untrusted. Archive limits,
  image decode budgets, and input validation are required (see
  [docs/security/threat-model.md](docs/security/threat-model.md)).
- **No secrets:** the repo contains no credentials. If that changes, use a secret
  manager and never commit keys.
- **Dependencies:** run `cargo audit`/`npm audit` equivalents and review
  advisories when the web work begins. `fractalnow` is an external binary and is
  dropped from the web scope.

Do not report issues in third-party dependencies here; report them upstream.

---

Part of the project docs. Index: [docs/README.md](docs/README.md).
