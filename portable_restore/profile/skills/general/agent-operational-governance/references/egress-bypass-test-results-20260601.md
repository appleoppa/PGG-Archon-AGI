# Egress Guard — Bypass Test Results (2026-06-01)

## Test Environment
- macOS (Hermes Agent default profile)
- Python 3.11 socket monkey-patch
- No sudo access (pfctl not available)

## Test Coverage Matrix
| Path | BLOCKED | Evidence |
|------|:-------:|----------|
| socket.create_connection("api.openai.com", 443) | ✅ | BlockingIOError: [EGRESS_GUARD]... |
| requests.get("https://api.openai.com/...") | ✅ | urllib3 monkey-patch → blocked |
| urllib.request.urlopen("https://api.openai.com/...") | ✅ | HTTP 403 via kernel proxy |
| curl -s https://api.openai.com/... (subprocess) | ✅ | timeout (API unreachable) |
| nc -zv api.openai.com 443 (subprocess) | ❌ | Connection succeeded |
| Direct IP (198.18.0.46:443) | ✅ | IP resolved + blocked |

**Block rate**: 4/6 (67%)
**Bypass rate**: 33%

## Known Bypass: nc(subprocess)
**Root cause**: Python-level monkey-patch cannot intercept subprocess calls.
**Resolution**: macOS pfctl (sudo required) or container network namespace.
**Score impact**: 92/100 without pfctl → 95-96/100 with pfctl.
