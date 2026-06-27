#!/usr/bin/env python3
"""
EVM运行反射桥接层
把EVM从事后评分公式，接入智能体任务执行的前置预判、执行中纠偏、结束后沉淀。
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from CoreFormula.EVM_FORMULA import EVMCore


SIGNAL_TO_DEFECT = {
    "context_overflow": "Tok",
    "tool_interrupt": "Clw",
    "multi_task_conflict": "Agt",
    "state_delay": "Pan",
    "prompt_ambiguity": "Prm",
    "weak_self_drive": "Soul",
    "execution_delay": "Run",
    "network_break": "Net",
    "hallucination_risk": "Err",
    "memory_not_used": "Mem",
    "resource_pressure": "Res",
    "missing_verification": "Log",
    "explanation_without_action": "Run",
    "ask_instead_of_act": "Soul",
}

DEFECT_ACTIONS = {
    "Tok": "收束上下文，只保留当前任务必要信息",
    "Clw": "换工具路径，失败后立即改用备用取证方式",
    "Agt": "拆分任务优先级，只保留一个当前主线",
    "Pan": "刷新状态，不依赖旧声明判断进度",
    "Prm": "把模糊指令转为最小可执行动作",
    "Soul": "先执行可逆小动作，不等待额外确认",
    "Run": "连续完成一个完整批次后再汇报",
    "Net": "切换检索或访问路径，不能因门禁放弃",
    "Err": "用文件、日志或运行结果校验结论",
    "Mem": "读取长期记忆并转化为当前动作约束",
    "Res": "减少工具调用，合并读取与验证",
    "Log": "保存验证结果和交接记录，防止只跑通不沉淀",
}


class EVMRuntimeBridge:
    """智能体运行层EVM桥。"""

    def __init__(self, trace_dir: Optional[str] = None):
        self.evm = EVMCore()
        self.task_id = None
        self.intent = None
        self.events: List[Dict] = []
        self.trace_dir = Path(trace_dir or Path(__file__).resolve().parents[1] / ".evm_runtime" / "traces")
        self.trace_dir.mkdir(parents=True, exist_ok=True)

    def start_task(self, task_id: str, intent: str, risk_signals: Optional[List[str]] = None) -> Dict:
        """任务开始前：识别风险并写入EVM缺陷。"""
        self.task_id = task_id
        self.intent = intent
        self.events = []
        for signal in risk_signals or []:
            self.observe(signal, severity=0.25, note="任务前风险预判")
        return self.snapshot(stage="start")

    def observe(self, signal: str, severity: float = 0.3, note: str = "") -> Dict:
        """执行中：把行为信号转为EVM十二类缺陷。"""
        defect = SIGNAL_TO_DEFECT.get(signal)
        if not defect:
            defect = "Err"
            note = note or "未知信号，按幻觉/错判风险处理"
        severity = max(0.0, min(1.0, float(severity)))
        self.evm.add_defect(defect, severity)
        event = {
            "time": datetime.now().isoformat(timespec="seconds"),
            "signal": signal,
            "defect": defect,
            "severity": severity,
            "note": note,
        }
        self.events.append(event)
        return event

    def recommend_actions(self) -> List[Dict]:
        """根据当前缺陷给出治理动作。"""
        status = self.evm.get_status()
        defects = status["defects_detail"]
        governance = status["governance_detail"]
        active = []
        for defect, value in defects.items():
            if value > 0:
                active.append({
                    "defect": defect,
                    "value": round(value, 4),
                    "governance_power": round(governance.get(defect, 0.0), 4),
                    "action": DEFECT_ACTIONS.get(defect, "先核实再行动"),
                })
        active.sort(key=lambda item: (item["value"], item["governance_power"]), reverse=True)
        return active

    def apply_governance(self) -> Dict:
        """执行中纠偏：把治理建议转成实际缺陷压降。"""
        status = self.evm.get_status()
        defects = status["defects_detail"]
        governance = status["governance_detail"]
        healed = {}
        for defect, value in defects.items():
            if value <= 0:
                continue
            power = governance.get(defect, 0.0)
            heal_value = value * power
            if heal_value > 0:
                self.evm.heal_defect(defect, heal_value)
                healed[defect] = round(heal_value, 4)
        self.events.append({
            "time": datetime.now().isoformat(timespec="seconds"),
            "signal": "governance_applied",
            "healed": healed,
        })
        return {"healed": healed, "snapshot": self.snapshot(stage="governed")}

    def close_task(self, outcome_score: float, learned: str, persisted: bool) -> Dict:
        """任务结束后：验证、沉淀并保存轨迹。"""
        outcome_score = max(0.0, min(1.0, float(outcome_score)))
        if outcome_score < 0.75:
            self.observe("missing_verification", 0.2, "结果低于可交付阈值")
        if not persisted:
            self.observe("missing_verification", 0.25, "跑通但未沉淀")
        summary = self.snapshot(stage="closed")
        summary["outcome_score"] = outcome_score
        summary["learned"] = learned
        summary["persisted"] = persisted
        self._save_trace(summary)
        return summary

    def snapshot(self, stage: str) -> Dict:
        status = self.evm.get_status()
        return {
            "task_id": self.task_id,
            "intent": self.intent,
            "stage": stage,
            "evm_value": round(status["evm_value"], 4),
            "raw_defect_rate": round(status["raw_defect_rate"], 4),
            "governed_defect_rate": round(status["governed_defect_rate"], 4),
            "governance_reduction": round(status["governance_reduction"], 4),
            "active_defects": {k: round(v, 4) for k, v in status["defects_detail"].items() if v > 0},
            "recommendations": self.recommend_actions() if stage != "recommend_only" else [],
            "events": list(self.events),
        }

    def _save_trace(self, summary: Dict):
        date = datetime.now().strftime("%Y%m%d")
        path = self.trace_dir / f"evm_runtime_trace_{date}.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(summary, ensure_ascii=False) + "\n")


__all__ = ["EVMRuntimeBridge", "SIGNAL_TO_DEFECT", "DEFECT_ACTIONS"]
