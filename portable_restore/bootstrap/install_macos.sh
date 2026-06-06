#!/usr/bin/env bash
set -euo pipefail
DRY_RUN="${DRY_RUN:-0}"
run(){ if [ "$DRY_RUN" = "1" ]; then echo "DRY_RUN $*"; else "$@"; fi; }
echo "PGG Archon portable install helper"
echo "This script intentionally does not install secrets. Fill config-templates/env.example locally."
command -v git >/dev/null || { echo "BLOCKED git missing"; exit 1; }
command -v python3 >/dev/null || { echo "BLOCKED python3 missing"; exit 1; }
if ! command -v node >/dev/null; then echo "WARN node missing; Hermes Web UI may need Node v24.x"; fi
if ! command -v cargo >/dev/null && [ ! -x "$HOME/.cargo/bin/cargo" ]; then echo "WARN cargo missing; Rust PyO3 modules need Rust toolchain"; fi
echo "INSTALL_PREREQ_CHECK_OK"
