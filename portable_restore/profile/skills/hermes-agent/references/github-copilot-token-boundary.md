# GitHub Copilot vs GitHub API Token Boundary

Use this when Hermes/Copilot logs warn that `GH_TOKEN` or `GITHUB_TOKEN` is unsupported by the Copilot API, especially classic PAT (`ghp_*`) warnings.

## Rule

Keep Copilot authentication separate from ordinary GitHub API authentication:

- `COPILOT_GITHUB_TOKEN`: Copilot API only. Must be a supported Copilot token type such as OAuth `gho_*`, fine-grained `github_pat_*` with Copilot Requests permission, or GitHub App `ghu_*`.
- `GH_TOKEN` / `GITHUB_TOKEN`: GitHub API, GitHub CLI, Skills Hub, GitHub Actions, repository/API workflows. Do not treat these as Copilot candidates unless the implementation explicitly validates that they are Copilot-supported.

## Why

If Hermes loads ordinary GitHub tokens into the Copilot provider path, classic PATs can trigger repeated warnings like:

- `Token from GH_TOKEN is not supported: Classic Personal Access Tokens (ghp_*) are not supported by the Copilot API`
- `Token from GITHUB_TOKEN is not supported...`

This is not a GitHub API failure. It is a provider-boundary issue: the Copilot path is trying the wrong token class.

## Repair pattern

1. Check the Copilot provider profile and auth registry for env var lists.
2. Keep Copilot provider env vars narrowed to `COPILOT_GITHUB_TOKEN` unless the code explicitly filters unsupported token prefixes before logging or trying them.
3. Keep docs aligned:
   - Copilot docs: `COPILOT_GITHUB_TOKEN` or OAuth via `hermes model`; `gh auth token` only if it returns a supported Copilot token type.
   - GitHub API / Skills Hub / Actions docs: `GH_TOKEN` / `GITHUB_TOKEN` are acceptable ordinary GitHub tokens.
4. Update tests that assert provider env var order; otherwise tests will preserve the old mixed-token behavior.
5. Do not delete or rewrite the user's `GH_TOKEN` / `GITHUB_TOKEN` just to fix Copilot warnings; they may be valid for GitHub API workflows.

## Verification

Search for stale Copilot wording in active docs/code:

- `COPILOT_GITHUB_TOKEN", "GH_TOKEN", "GITHUB_TOKEN"`
- `GITHUB_TOKEN or gh auth token`
- `GH_TOKEN environment variable` in Copilot-specific sections
- `GITHUB_TOKEN environment variable` in Copilot-specific sections

Historical archives may retain old wording; do not rewrite archives unless the user asks for archival cleanup.
