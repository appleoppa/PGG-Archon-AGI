#!/usr/bin/env bash
set -euo pipefail
TARGET_HOME="${TARGET_HOME:-$HOME}"
HERMES_DIR="$TARGET_HOME/.hermes"
fail=0
check_file(){ if [ -s "$1" ]; then echo "PASS file $1"; else echo "FAIL missing_or_empty $1"; fail=1; fi; }
check_dir(){ if [ -d "$1" ]; then echo "PASS dir $1"; else echo "FAIL missing_dir $1"; fail=1; fi; }
check_file "$HERMES_DIR/SOUL.md"
check_file "$HERMES_DIR/memories/MEMORY.md"
check_file "$HERMES_DIR/memories/USER.md"
check_file "$HERMES_DIR/data/EVOLUTION_MANIFEST.json"
check_dir "$HERMES_DIR/skills"
python3 - <<PY
import json, pathlib, sys, os
p=pathlib.Path(os.environ.get('TARGET_HOME', pathlib.Path.home()))/'.hermes/data/EVOLUTION_MANIFEST.json'
try:
    data=json.loads(p.read_text())
except Exception as e:
    print('FAIL manifest_json', e); sys.exit(2)
required=['generated_at','last_updated']
print('PASS manifest_json top_level_count=%d' % len(data))
print('INFO manifest_keys_sample=' + ','.join(list(data)[:12]))
PY
if command -v python3 >/dev/null; then echo "PASS python3 $(python3 --version 2>&1)"; else echo "WARN python3_missing"; fi
if command -v git >/dev/null; then echo "PASS git $(git --version)"; else echo "WARN git_missing"; fi
if command -v node >/dev/null; then echo "INFO node $(node --version)"; else echo "WARN node_missing"; fi
if command -v cargo >/dev/null; then echo "INFO cargo $(cargo --version)"; elif [ -x "$HOME/.cargo/bin/cargo" ]; then echo "INFO cargo $($HOME/.cargo/bin/cargo --version)"; else echo "WARN cargo_missing"; fi
if [ "$fail" -eq 0 ]; then echo "VERIFY_OK"; else echo "VERIFY_FAIL"; exit 1; fi
