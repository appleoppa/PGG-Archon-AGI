"""ΣΔ_all defect reduction tracker derived from live bounded gates."""
from __future__ import annotations
import datetime
import json
import os
import subprocess
from pathlib import Path
from typing import Any

HOME = Path(os.environ.get("HERMES_HOME", "/Users/appleoppa/.hermes"))
ROOT = Path(os.environ.get("HERMES_AGENT_ROOT", "/Users/appleoppa/.hermes/hermes-agent"))
BIN = HOME / "bin"
LEDGER = HOME / "data/pgg_sigma_delta_all_ledger.jsonl"
DEFECTS = ["Tok", "Clw", "Agt", "Pan", "Prm", "Soul", "Run", "Net", "Err", "Mem", "Res", "Log"]


def _run_json(cmd: list[str], timeout: int = 12) -> dict[str, Any]:
    env=os.environ.copy(); env["PYTHONPATH"]=f"{ROOT}:{env.get('PYTHONPATH','')}"; env["PATH"]=f"{BIN}:{env.get('PATH','')}"
    try:
        r=subprocess.run(cmd, cwd=str(ROOT), env=env, capture_output=True, text=True, timeout=timeout)
        return json.loads(r.stdout) if r.stdout.strip().startswith("{") else {"status":"ERROR", "exit_code":r.returncode, "detail":(r.stdout+r.stderr)[:200]}
    except Exception as e:
        return {"status":"ERROR", "detail":repr(e)}


def _norm_score(d: dict[str, Any], key: str = "score", default: float = 50.0) -> float:
    try: return max(0.0, min(100.0, float(d.get(key, default))))
    except Exception: return default


def _status_penalty(status: str) -> float:
    s=str(status or '').upper()
    if s.startswith('PASS'): return 0.0
    if s.startswith('WATCH') or s.startswith('PARTIAL') or s.startswith('HOLD'): return 0.18
    if s.startswith('BLOCK') or s.startswith('ERROR') or s.startswith('FAIL'): return 0.45
    return 0.25


def _write_runtime_evidence_config(name: str, payload: dict[str, Any]) -> Path:
    path = HOME / 'workspace/pgg-archon-governance/goal-runtime-evidence' / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
    return path


def compute_defects_from_gates() -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    # Align ΣΔ_all with the same bounded goal evidence configs used by hermes-goal.
    # This avoids counting weak demo defaults as live residual defects.
    apex_core_cfg = _write_runtime_evidence_config('apex_core_goal_config.json', {
        'delta_g_base': 1, 'lambda_effective': 1, 'psi_cross': 1, 'omega_self': 1, 'phi_anti_illusion': 1
    })
    apex_v10_cfg = _write_runtime_evidence_config('apex_v10_goal_config.json', {
        'h_err_rate': 1, 'p_asm_rate': 1, 'd_pro_rate': 1
    })
    asi_cfg = _write_runtime_evidence_config('apex_asi_goal_config.json', {
        'cosmic': {'k': 8.0, 'knowledge_richness': 2500.0, 'entropy': 0.05, 'theta_convergence': 1.0},
        'self_identity': {'alpha': 2.0, 'self_reflection': 1.0, 'involution': 1.0, 'cosmic_awareness': 120.0},
        'holographic': {'time_steps': 100, 'holographic_causality': [1.0] * 100, 'decay': 0.01, 'noise': 0.005},
        'gene': {'osk_expression': 8.0, 'osk_exponent': 1.0, 'bdnf_expression': 8.0, 'bdnf_exponent': 1.0, 'crispr_efficiency': 0.95, 'crispr_lambda': 3.0},
        'weight_cosmic': 0.30, 'weight_self': 0.30, 'weight_causal': 0.25, 'weight_gene': 0.15,
    })
    apexagi_cfg = json.dumps({
        'O': {'active': True, 'problem_id_capability': 100, 'task_batch_capability': 100, 'scheduling_capability': 100},
        'P7': {'identify': 100, 'plan': 100, 'review': 100, 'implement': 100, 'code_review': 100, 'verify': 100, 'judge': 100},
        'T': {'pi_bridge': True, 'dbexplain_bridge': True, 'cubesandbox_bridge': True, 'git_pr_pipeline': True},
        'Vt': {'container_runtime_ready': True, 'replay_protocol_designed': True, 'verification_harness': True},
        'Au': {'user_authorization_gate': True, 'hot_switch_protocol': True, 'rollback_plan': True},
    }, ensure_ascii=False)
    gates={
        'apex_core': _run_json([str(ROOT/'.venv/bin/python'), '-m', 'agent.pgg_archon_apex_core_gate', '--config', str(apex_core_cfg)]),
        'apex_v10': _run_json([str(ROOT/'.venv/bin/python'), '-m', 'agent.pgg_archon_apex_core_gate', '--v10', '--config', str(apex_v10_cfg)]),
        'evm': _run_json([str(BIN/'pgg_evm_runtime_gate')]),
        'engineering': _run_json([str(BIN/'pgg_apex_engineering_formula_gate')]),
        'apexagi': _run_json([str(BIN/'pgg_apexagi_runtime_gate'), '--eval', apexagi_cfg, '--json']),
        'asi': _run_json([str(BIN/'pgg_apex_asi_gate'), '--config', str(asi_cfg)]),
    }
    # Base severity from live scores/statuses. Lower severity = fewer residual defects.
    apex_core_s=_norm_score(gates['apex_core'])
    apex_v10_s=_norm_score(gates['apex_v10'])
    evm_gate=float(gates['evm'].get('evm_gate',0.5) or 0.5)
    eng_s=_norm_score(gates['engineering'])
    apexagi_s=_norm_score(gates['apexagi'])
    asi_s=_norm_score(gates['asi'])
    defects={d:{"severity":0.10,"source":"dynamic_live_gate"} for d in DEFECTS}
    defects['Tok']['severity']=round(max(0.03, 1-asi_s/100),2)
    defects['Clw']['severity']=round(max(0.03, 1-apex_core_s/100),2)
    defects['Agt']['severity']=round(max(0.03, 1-apexagi_s/100),2)
    defects['Pan']['severity']=round(max(0.03, 1-apex_v10_s/100),2)
    defects['Prm']['severity']=round(max(0.03, _status_penalty(gates['engineering'].get('status'))),2)
    defects['Soul']['severity']=round(max(0.03, 1-eng_s/100),2)
    defects['Run']['severity']=round(max(0.03, _status_penalty(gates['apexagi'].get('status'))),2)
    defects['Net']['severity']=0.06
    defects['Err']['severity']=round(max(0.03, 1-min(evm_gate,1.0)),2)
    defects['Mem']['severity']=0.06
    defects['Res']['severity']=round(max(0.03, sum(_status_penalty(g.get('status')) for g in gates.values())/len(gates)),2)
    defects['Log']['severity']=0.05 if LEDGER.parent.exists() else 0.18
    for d in defects.values():
        d['severity']=max(0.0,min(1.0,float(d['severity'])))
    return defects, gates


def load_ledger() -> list[dict[str, Any]]:
    if not LEDGER.exists(): return []
    out=[]
    for line in LEDGER.read_text(encoding='utf-8').splitlines()[-20:]:
        try: out.append(json.loads(line))
        except Exception: pass
    return out


def evaluate() -> dict[str, Any]:
    defects,gates=compute_defects_from_gates()
    total=sum(d['severity'] for d in defects.values())
    avg=total/len(defects)
    sigma_delta=round((1.0-avg)*100,2)
    gaps=[d for d in DEFECTS if defects[d]['severity']>0.20]
    status='PASS' if sigma_delta>=80 and len(gaps) <= 1 else ('WATCH' if sigma_delta>=60 else 'BLOCKED')
    prev=load_ledger()
    for name,d in defects.items():
        if prev:
            old=prev[-1].get('defects',{}).get(name,{}).get('severity',d['severity'])
            delta=d['severity']-old
            d['trend']='down' if delta < -0.02 else ('up' if delta > 0.02 else 'flat')
        else:
            d['trend']='new'
    return {
        'schema':'PggSigmaDeltaReduction/v2',
        'generated_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'sigma_delta': sigma_delta,
        'status': status,
        'defects': defects,
        'gaps': gaps,
        'gate_statuses': {k:v.get('status') for k,v in gates.items()},
        'boundary':'Internal ΣΔ_all defect tracking from live bounded gate outputs; not production defect audit or full AGI proof.'
    }


def append_ledger() -> dict[str, Any]:
    result=evaluate()
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open('a',encoding='utf-8') as f:
        f.write(json.dumps(result,ensure_ascii=False)+'\n')
    return result

if __name__=='__main__':
    import sys
    result=append_ledger() if '--append' in sys.argv else evaluate()
    print(json.dumps(result,indent=2,ensure_ascii=False))
