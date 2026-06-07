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
CRATES=(hermes_pgg_status hermes_pgg_ecc hermes_pgg_overlay hermes_pgg_ralph hermes_pgg_pilotdeck hermes_pgg_github_evolution_gate hermes_pgg_kanban_gate hermes_pgg_context_learning_gate hermes_pgg_context_formula_gate hermes_pgg_global_trajectory_gate hermes_pgg_personal_agent_training_gate hermes_pgg_research_engine hermes_pgg_strata_apex_gate hermes_pgg_book_to_skill hermes_pgg_apex_delta_e_gate hermes_pgg_apex_god_evidence_gate hermes_pgg_memory_swrs_gate hermes_pgg_team_memory_gate hermes_pgg_department_memory_apply_gate hermes_pgg_department_memory_distillation_gate hermes_pgg_department_memory_review_gate hermes_pgg_evomaster_gate hermes_pgg_tiangong_gate hermes_pgg_devour_evolution_gate hermes_pgg_evomap_driver hermes_pgg_cmmi_industrial_gate hermes_apex_delta_g)

export PYO3_PYTHON="$PYTHON_BIN"

for crate in "${CRATES[@]}"; do
  if [[ ! -d "$BASE/$crate" ]]; then
    echo "==> skip missing $crate"
    continue
  fi
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
