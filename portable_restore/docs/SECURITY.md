# Security Boundary

Do not commit real secrets. This restore bundle is designed to be GitHub-safe only if secret scans pass.

Forbidden patterns in this tree:

- `.env` with real values
- `auth.json`
- private keys
- provider API keys
- OAuth refresh/access tokens
- client legal materials

Run `bootstrap/verify_runtime.sh` after restore and run repository secret scans before push.
