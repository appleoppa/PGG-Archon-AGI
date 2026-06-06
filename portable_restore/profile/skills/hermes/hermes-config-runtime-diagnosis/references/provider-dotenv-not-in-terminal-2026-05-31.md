## Verification

- [x] `hermes doctor` shows ✓ MiniMax (China) (key configured)
- [x] `hermes auth list` shows minimax-cn with MINIMAX_CN_API_KEY source
- [x] Direct API test via Hermes credential resolution returns HTTP 200
- [x] Configuration is structurally correct (providers + custom_providers + key_env aligned)
- [x] The `.env` file is NOT auto-loaded in terminal, which is the root cause of manual curl failures

## Skill Update Summary (2026-05-31)

- **Added** ⚠️ Key Pitfall: `.env` Not Auto-Loaded in Terminal to SKILL.md
- **Added** "Test via Hermes Credential System" section after "Extract keys safely when needed"
- **Added** `references/provider-dotenv-not-in-terminal-2026-05-31.md` with full reproduction, resolution options, and MiniMax China endpoint details
- **Updated** Support References list to include the new reference file
