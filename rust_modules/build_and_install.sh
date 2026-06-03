#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/appleoppa/.hermes/hermes-agent"
BASE="$ROOT/rust_modules"
SITE="$ROOT/venv/lib/python3.11/site-packages"
CRATES=(hermes_pgg_status hermes_pgg_ecc hermes_pgg_overlay)

export PYO3_PYTHON="$ROOT/venv/bin/python"

for crate in "${CRATES[@]}"; do
  echo "==> build $crate"
  (cd "$BASE/$crate" && cargo build --release)
  src="$BASE/$crate/target/release/lib${crate}.dylib"
  dest="$SITE/${crate}.abi3.so"
  test -f "$src"
  cp "$src" "$dest"
  codesign --remove-signature "$dest" 2>/dev/null || true
  codesign --force --sign - "$dest"
  "$ROOT/venv/bin/python" - <<PY
import importlib, json
m=importlib.import_module('$crate')
print(json.dumps({'module':'$crate','version':m.version(),'file':getattr(m,'__file__',None)}, ensure_ascii=False))
PY
  shasum -a 256 "$dest"
done

echo "==> hermes_*.so installed"
find "$SITE" -maxdepth 1 -name 'hermes_*.so' -print | sort
