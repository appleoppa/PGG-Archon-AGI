#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${HERMES_AGENT_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"
BASE="$ROOT/rust_modules"
PYTHON_BIN="${PYO3_PYTHON:-$ROOT/venv/bin/python}"
SITE="${HERMES_PY_SITE:-$($PYTHON_BIN - <<'PY'
import site
print(site.getsitepackages()[0])
PY
)}"
CRATES=(hermes_pgg_status hermes_pgg_ecc hermes_pgg_overlay hermes_pgg_ralph hermes_pgg_pilotdeck)

export PYO3_PYTHON="$PYTHON_BIN"

for crate in "${CRATES[@]}"; do
  echo "==> build $crate"
  (cd "$BASE/$crate" && cargo build --release)
  src="$BASE/$crate/target/release/lib${crate}.dylib"
  dest="$SITE/${crate}.abi3.so"
  test -f "$src"
  cp "$src" "$dest"
  codesign --remove-signature "$dest" 2>/dev/null || true
  codesign --force --sign - "$dest"
  "$PYTHON_BIN" - <<PY
import importlib, json
m=importlib.import_module('$crate')
print(json.dumps({'module':'$crate','version':m.version(),'file':getattr(m,'__file__',None)}, ensure_ascii=False))
PY
  shasum -a 256 "$dest"
done

echo "==> hermes_*.so installed"
find "$SITE" -maxdepth 1 -name 'hermes_*.so' -print | sort
