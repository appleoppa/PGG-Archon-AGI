"""
河图洛书 ABD 三模型辩论层
==========================
定位：PGG Archon 决策辅助辩论系统
模型分配：A=GPT-5.5 / B=DeepSeek-v4-flash / D=MiniMax-M2.7-highspeed

触发条件：用户消息包含触发词（河图洛书/三模型辩论/ABD辩论/三模型讨论）
执行流程：
  1. 检测触发词
  2. 构建三模型辩论 prompt（各角色定位清晰）
  3. 并行调用 A、B、D 三个模型
  4. 收集各方观点，形成《辩论结论》
  5. 由主模型（A）综合输出最终决策建议

设计原则：
  - 三方各有分工，不做重复劳动
  - 辩论结果作为 PGG Archon 决策参考，不自动执行
  - 有完整超时/降级/异常处理
"""

import json
import logging
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class ModelSlot(Enum):
    A = "A"  # GPT-5.5 架构推理型
    B = "B"  # DeepSeek 事实检索型
    D = "D"  # MiniMax 轻量响应型


@dataclass
class DebateTurn:
    round_num: int
    speaker: ModelSlot
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class DebateResult:
    task: str                          # 原始问题
    rounds: list[DebateTurn]           # 辩论过程
    final_summary: str                 # A 模型综合结论
    vote_count: dict[str, int]        # {A/B/D}: int，各模型支持度自评
    decision: str                     # 最终决策建议
    confidence: float                 # 0.0~1.0，置信度
    meta: dict                        # 元信息（耗时、token消耗等）
    status: str = "ok"                # ok / partial / timeout / error
    error_msg: str = ""

    def to_dict(self) -> dict:
        return {
            "task": self.task,
            "rounds": [asdict(t) for t in self.rounds],
            "final_summary": self.final_summary,
            "vote_count": self.vote_count,
            "decision": self.decision,
            "confidence": self.confidence,
            "meta": self.meta,
            "status": self.status,
            "error_msg": self.error_msg,
            "debut_time": self.rounds[0].timestamp if self.rounds else "",
        }

    def save(self, path: Optional[Path] = None) -> Path:
        if path is None:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = Path(f"~/.hermes/hetu_luoshu/debate_{ts}.json").expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
        return path


_DEBATE_SYSTEM_PROMPT = """你是河图洛书辩论系统的模型参与方。

角色分配：
- A（GPT-5.5）：架构推理型，擅长复杂规划、系统设计、跨域综合推理
- B（DeepSeek-v4-flash）：事实检索型，擅长中文处理、法律检索、快速查证
- D（MiniMax-M2.7-highspeed）：轻量响应型，擅长日常任务、快速反馈、简洁输出

你的角色是：{role}

辩论任务：{task}

请根据你的角色定位，针对任务给出专业、简洁的观点（中文回答，200字以内）。
格式：
【{slot}模型观点】
你的核心论点：...
支持/反对理由：...
建议行动：...
"""


def _load_config() -> dict:
    """从 config.yaml 加载 hetu_luoshu 配置"""
    try:
        from hermes_cli.config import load_config
        cfg = load_config() or {}
        return cfg.get("hetu_luoshu", {})
    except Exception:
        return {}


def _should_trigger(user_message: str) -> bool:
    """检测是否应触发河图洛书辩论"""
    cfg = _load_config()
    if not cfg.get("enabled", False):
        return False
    if not cfg.get("require_trigger", True):
        return True
    triggers = cfg.get("trigger_phrases", [])
    msg_lower = user_message.lower()
    return any(t.lower() in msg_lower for t in triggers)


def _call_model(slot: ModelSlot, task: str, timeout: int = 120) -> tuple[str, dict]:
    """
    调用对应模型，返回 (content, meta)
    meta 包含 token 消耗和耗时
    """
    import os

    cfg = _load_config()
    model_map = cfg.get("models", {})
    slot_cfg = model_map.get(slot.value, {})
    model_name = slot_cfg.get("model", "")
    provider = slot_cfg.get("provider", "")
    role = slot_cfg.get("role", "")
    timeout = cfg.get("debate_timeout", timeout)

    # 从 provider 名解析 API 配置
    # 格式：custom:xxx → 从 config.yaml custom_providers 读取
    if provider.startswith("custom:"):
        provider_key = provider.split(":", 1)[1]
        try:
            from hermes_cli.config import load_config
            full_cfg = load_config() or {}
            cp_list = full_cfg.get("custom_providers", [])
            cp = next((p for p in cp_list if p.get("name") == provider_key), {})
        except Exception:
            cp = {}
    else:
        cp = {}

    api_mode = cp.get("api_mode", "")
    base_url = cp.get("base_url", "")
    key_env = cp.get("key_env", "")
    api_key = os.environ.get(key_env, "")

    start = time.time()
    content = ""
    meta = {"slot": slot.value, "model": model_name, "provider": provider, "elapsed": 0, "tokens_in": 0, "tokens_out": 0, "error": ""}

    try:
        if api_mode == "codex_responses":
            # GPT-5.5 / Claude
            import requests
            payload = {
                "model": model_name,
                "input": _DEBATE_SYSTEM_PROMPT.format(slot=slot.value, role=role, task=task),
                "max_output_tokens": 400,
            }
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            resp = requests.post(f"{base_url}/responses", json=payload, headers=headers, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            content = data.get("output", [{}])[0].get("content", [{}])[0].get("text", "") if isinstance(data.get("output"), list) else str(data)
            meta["tokens_in"] = data.get("usage", {}).get("input_tokens", 0)
            meta["tokens_out"] = data.get("usage", {}).get("output_tokens", 0)
        elif api_mode == "chat_completions":
            # DeepSeek
            import requests
            payload = {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": _DEBATE_SYSTEM_PROMPT.format(slot=slot.value, role=role, task=task)},
                ],
                "max_tokens": 400,
            }
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            resp = requests.post(f"{base_url}/chat/completions", json=payload, headers=headers, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            choices = data.get("choices", [])
            content = choices[0].get("message", {}).get("content", "") if choices else ""
            usage = data.get("usage", {})
            meta["tokens_in"] = usage.get("prompt_tokens", 0)
            meta["tokens_out"] = usage.get("completion_tokens", 0)
        elif api_mode == "anthropic_messages":
            # MiniMax
            import requests
            payload = {
                "model": model_name,
                "messages": [
                    {"role": "user", "content": _DEBATE_SYSTEM_PROMPT.format(slot=slot.value, role=role, task=task)},
                ],
                "max_tokens": 400,
            }
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            resp = requests.post(f"{base_url}/messages", json=payload, headers=headers, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            content = data.get("content", [{}])[0].get("text", "") if isinstance(data.get("content"), list) else ""
            usage = data.get("usage", {})
            meta["tokens_in"] = usage.get("input_tokens", 0)
            meta["tokens_out"] = usage.get("output_tokens", 0)
        else:
            content = f"[错误] 不支持的 api_mode: {api_mode}"
            meta["error"] = f"unsupported api_mode: {api_mode}"
    except Exception as e:
        content = f"[错误] 模型调用失败: {type(e).__name__}: {e}"
        meta["error"] = f"{type(e).__name__}: {e}"
        logger.warning("河图洛书 %s 调用失败: %s", slot.value, e)

    meta["elapsed"] = round(time.time() - start, 2)
    return content, meta


def run_debate(task: str, max_rounds: int = 3) -> DebateResult:
    """
    执行完整的三模型辩论流程
    1. 并行调用 A、B、D 三个模型（第一轮）
    2. 收集各方观点
    3. 由主模型（A）综合输出结论
    """
    cfg = _load_config()
    max_rounds = cfg.get("max_rounds", max_rounds)
    debate_timeout = cfg.get("debate_timeout", 120)
    rounds: list[DebateTurn] = []
    meta = {"total_rounds": 0, "models_called": [], "total_tokens_in": 0, "total_tokens_out": 0, "total_elapsed": 0.0}

    from concurrent import futures as _cf

    try:
        # 第一轮：并行调用三模型
        with _cf.ThreadPoolExecutor(max_workers=3) as _ex:
            _futures = {
                _ex.submit(_call_model, ModelSlot.A, task, debate_timeout): ModelSlot.A,
                _ex.submit(_call_model, ModelSlot.B, task, debate_timeout): ModelSlot.B,
                _ex.submit(_call_model, ModelSlot.D, task, debate_timeout): ModelSlot.D,
            }
            for _future in _cf.as_completed(_futures, timeout=debate_timeout + 10):
                _slot = _futures[_future]
                try:
                    content, call_meta = _future.result()
                except Exception as e:
                    content = f"[超时/异常] {type(e).__name__}: {e}"
                    call_meta = {"slot": _slot.value, "error": str(e), "elapsed": 0, "tokens_in": 0, "tokens_out": 0}
                rounds.append(DebateTurn(round_num=1, speaker=_slot, content=content))
                meta["models_called"].append(_slot.value)
                meta["total_tokens_in"] += call_meta.get("tokens_in", 0)
                meta["total_tokens_out"] += call_meta.get("tokens_out", 0)
                meta["total_elapsed"] = max(meta["total_elapsed"], call_meta.get("elapsed", 0))

        meta["total_rounds"] = len(rounds)

        # 汇总辩论内容供 A 模型综合
        debate_summary = "\n\n".join(
            f"【{r.speaker.value}模型】{r.content}" for r in sorted(rounds, key=lambda x: x.speaker.value)
        )

        # 第二轮：A 模型综合输出结论
        synthesis_prompt = f"""你是河图洛书辩论系统的 A 模型（主脑，架构推理型）。

以下是一场辩论中 A、B、D 三个模型的观点：

{debate_summary}

请综合三方观点，给出：
1. 三方核心分歧点
2. 各方最合理的建议
3. 最终决策建议（你作为主脑的判断）
4. 置信度评分（0.0~1.0，仅数字）

格式（中文回答，总字数不超过 300）：
【综合结论】
核心分歧：...
最终建议：...
置信度：X.XX
"""

        summary_content, summary_meta = _call_model(ModelSlot.A, synthesis_prompt, debate_timeout)
        meta["total_tokens_in"] += summary_meta.get("tokens_in", 0)
        meta["total_tokens_out"] += summary_meta.get("tokens_out", 0)
        meta["total_elapsed"] += summary_meta.get("elapsed", 0)

        # 解析置信度
        confidence = 0.5
        for line in summary_content.splitlines():
            if "置信度" in line or "confidence" in line.lower():
                import re
                m = re.search(r'0?\.\d+', line)
                if m:
                    confidence = float(m.group())

        # 投票计数（从各模型输出提取支持度）
        vote_count = {"A": 0, "B": 0, "D": 0}
        for r in rounds:
            if "建议" in r.content or "支持" in r.content:
                vote_count[r.speaker.value] += 1

        result = DebateResult(
            task=task,
            rounds=rounds,
            final_summary=summary_content,
            vote_count=vote_count,
            decision=summary_content,
            confidence=confidence,
            meta=meta,
            status="ok",
        )

    except _cf.TimeoutError:
        result = DebateResult(
            task=task, rounds=rounds, final_summary="", vote_count={}, decision="[超时] 辩论未完成",
            confidence=0.0, meta=meta, status="timeout", error_msg="三模型辩论整体超时"
        )
    except Exception as e:
        logger.warning("河图洛书辩论异常: %s", e)
        result = DebateResult(
            task=task, rounds=rounds, final_summary="", vote_count={}, decision=f"[错误] {e}",
            confidence=0.0, meta=meta, status="error", error_msg=str(e)
        )

    # 保存辩论记录
    saved_path = result.save()
    result.meta["saved_path"] = str(saved_path)
    logger.info("河图洛书辩论完成，保存至: %s", saved_path)
    return result


def format_debate_report(result: DebateResult) -> str:
    """将辩论结果格式化为可读报告"""
    lines = [
        "## 河图洛书 ABD 辩论报告",
        "",
        f"**任务**: {result.task}",
        f"**状态**: {result.status.upper()}",
        f"**置信度**: {result.confidence:.2f}",
        "",
        "### 辩论过程",
    ]
    for r in sorted(result.rounds, key=lambda x: x.speaker.value):
        lines.append(f"\n**【{r.speaker.value} 模型】**")
        lines.append(r.content.strip())

    lines.append("\n### 综合结论（A模型主脑）")
    lines.append(result.final_summary.strip() if result.final_summary else result.decision)

    lines.append(f"\n> 辩论记录已保存: `{result.meta.get('saved_path', 'N/A')}`")
    lines.append(f"> 耗时: {result.meta.get('total_elapsed', 0):.1f}s | ")
    lines.append(f"Token消耗: in={result.meta.get('total_tokens_in', 0)} / out={result.meta.get('total_tokens_out', 0)}")

    return "\n".join(lines)


# ── CLI 入口 ──────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="河图洛书 ABD 三模型辩论")
    parser.add_argument("task", help="辩论任务/问题")
    parser.add_argument("--rounds", type=int, default=3, help="最大辩论轮次")
    args = parser.parse_args()

    result = run_debate(args.task, args.rounds)
    print(format_debate_report(result))
