"""
PGG Archon 办案专用 4 通道 LLM 薄壳。
- 用 super_evolution_card._PROVIDERS + _ask
- 强制 STRICT JSON 模式（system prompt 末尾追加 JSON ONLY + 字段契约）
- 每通道独立记录 http_status / visible_chars / verdict
- 单通道失败不冒充 PASS，按 ERROR/UNKNOWN 标
"""
from __future__ import annotations
import json, sys, time, os
from typing import Any
from pathlib import Path

# 让 super_evolution_card 可导入
HERMES = os.path.expanduser("~/.hermes/hermes-agent")
sys.path.insert(0, HERMES)

from agent.pgg_archon_super_evolution_card import _PROVIDERS, _ask, _read_env  # noqa: E402

# claude 当前按用户指示保持 ERROR，办案通道不调用
BANNED = {"claude"}

# 4 通道 filter（minimax 默认保留以观察健康度，可由调用方再剔除）
CASE_PROVIDERS = [p for p in _PROVIDERS if p[0] not in BANNED]


def call_one(label: str, prompt: str, json_mode: bool = True, max_tokens: int | None = None,
             timeout: int = 90) -> dict[str, Any]:
    """单通道单问单答。返回 {label, http_status, visible_chars, verdict, content, error, elapsed_s}。"""
    cfg = next((p for p in _PROVIDERS if p[0] == label), None)
    if not cfg:
        return {"label": label, "verdict": "ERROR", "error": f"unknown label {label}"}
    if label in BANNED:
        return {"label": label, "verdict": "ERROR", "error": "provider banned (claude unavailable)"}
    plabel, model, url, env, mode, default_mx = cfg
    key = _read_env(env)
    if not key:
        return {"label": label, "verdict": "ERROR", "error": f"missing env {env}"}

    final_prompt = prompt
    if json_mode:
        final_prompt = prompt + "\n\n===严格输出约束===\n只输出 STRICT JSON，不要任何解释、Markdown、代码块、注释。键必须用双引号。"

    mx = max_tokens or default_mx
    started = time.time()
    try:
        import requests
        h = {"Authorization": "Bearer " + key, "Content-Type": "application/json"}
        pl = {
            "model": model, "messages": [{"role": "user", "content": final_prompt}],
            "max_tokens": mx, "temperature": 0.2,
        }
        r = requests.post(url, headers=h, json=pl, timeout=timeout)
        http_status = r.status_code
        if r.status_code != 200:
            return {"label": label, "http_status": http_status, "verdict": "ERROR",
                    "error": r.text[:300], "elapsed_s": round(time.time()-started, 1)}
        j = r.json()
        content = str((j.get("choices") or [{}])[0].get("message", {}).get("content") or "")
        # verdict 严格分类
        if not content.strip():
            verdict = "ERROR"  # 0-char 是 transient 失败信号，绝不冒充
        else:
            try:
                obj = json.loads(content.strip().strip("```json").strip("```").strip())
                verdict = "PASS" if isinstance(obj, dict) else "WATCH"
            except Exception:
                if "{" in content and "}" in content:
                    verdict = "WATCH"
                else:
                    verdict = "WATCH"
        return {
            "label": label, "http_status": http_status, "visible_chars": len(content),
            "verdict": verdict, "content": content, "elapsed_s": round(time.time()-started, 1),
        }
    except Exception as e:
        return {"label": label, "verdict": "ERROR", "error": repr(e)[:300],
                "elapsed_s": round(time.time()-started, 1)}


def call_all(prompt: str, json_mode: bool = True, max_tokens: int | None = None,
             timeout: int = 90) -> dict[str, Any]:
    """4 通道并行调用，返回 {per_provider: [...], consensus: {...}}。"""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    out: dict[str, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = {ex.submit(call_one, lbl, prompt, json_mode, max_tokens, timeout): lbl for lbl, *_ in CASE_PROVIDERS}
        for f in as_completed(futs):
            lbl = futs[f]
            out[lbl] = f.result()
    n_pass = sum(1 for r in out.values() if r.get("verdict") == "PASS")
    n_watch = sum(1 for r in out.values() if r.get("verdict") == "WATCH")
    n_err = sum(1 for r in out.values() if r.get("verdict") == "ERROR")
    return {
        "per_provider": out,
        "consensus": {"PASS": n_pass, "WATCH": n_watch, "ERROR": n_err, "total": len(out)},
    }


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--ping", action="store_true", help="4 通道 ping")
    ap.add_argument("--prompt", type=str, help="自定义 prompt")
    ap.add_argument("--max-tokens", type=int, default=None)
    ap.add_argument("--timeout", type=int, default=90)
    args = ap.parse_args()

    if args.ping:
        prompt = "请用 STRICT JSON 格式回复：{\"ok\": true, \"provider\": \"<your name>\"}。仅此一个 JSON 对象。"
        result = call_all(prompt, json_mode=True, max_tokens=80, timeout=args.timeout)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.prompt:
        result = call_all(args.prompt, json_mode=True, max_tokens=args.max_tokens, timeout=args.timeout)
        print(json.dumps(result, ensure_ascii=False, indent=2))
