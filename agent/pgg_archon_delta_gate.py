"""PGG Archon ΔG 约束门 — 反幻觉检测核心模块.

ΔG (DeltaG) 约束门用于检测LLM输出中的幻觉内容。通过11个维度的参数测量，
计算总的 ΔG 值，并根据阈值判断内容是否可信。

11个测量维度：
  1. citation_accuracy    - 引用准确性（法条、判例编号是否真实存在）
  2. legal_term_consistency - 法律术语一致性（术语使用是否规范）
  3. logical_coherence     - 逻辑连贯性（推理链条是否完整）
  4. numerical_reasonability - 数值合理性（金额、日期等是否合理）
  5. temporal_consistency   - 时间一致性（时间引用是否自洽）
  6. source_attribution    - 来源归因（引述来源是否可验证）
  7. factual_density       - 事实密度（可验证事实占比）
  8. noise_ratio           - 噪声比率（无意义或矛盾内容占比）
  9. fidelity_score        - 保真度（与已知知识的一致程度）
  10. logic_chain_strength - 逻辑链强度（推理步骤完整度）
  11. context_relevance    - 上下文相关性（内容与主题的契合度）

状态判定：
  - ΔG < 0.30 → allowed (稳态，内容可信)
  - 0.30 ≤ ΔG < 0.60 → partial_repair (轻微偏离，需部分修复)
  - ΔG ≥ 0.60 → critical (临界状态，需完全修复)
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PARAMETER_NAMES: List[str] = [
    "citation_accuracy",
    "legal_term_consistency",
    "logical_coherence",
    "numerical_reasonability",
    "temporal_consistency",
    "source_attribution",
    "factual_density",
    "noise_ratio",
    "fidelity_score",
    "logic_chain_strength",
    "context_relevance",
]

# Weights for each parameter (sum = 1.0)
DEFAULT_WEIGHTS: Dict[str, float] = {
    "citation_accuracy": 0.15,
    "legal_term_consistency": 0.10,
    "logical_coherence": 0.12,
    "numerical_reasonability": 0.10,
    "temporal_consistency": 0.08,
    "source_attribution": 0.10,
    "factual_density": 0.10,
    "noise_ratio": 0.08,
    "fidelity_score": 0.07,
    "logic_chain_strength": 0.05,
    "context_relevance": 0.05,
}

# Gate thresholds
THRESHOLD_ALLOWED = 0.30
THRESHOLD_PARTIAL = 0.60

# ---------------------------------------------------------------------------
# Known legal references (for citation validation)
# ---------------------------------------------------------------------------

KNOWN_LAWS = {
    "民法典": {"max_article": 1260, "valid": True},
    "合同法": {"max_article": 428, "valid": True},
    "刑法": {"max_article": 452, "valid": True},
    "公司法": {"max_article": 266, "valid": True},
    "劳动法": {"max_article": 107, "valid": True},
    "消费者权益保护法": {"max_article": 63, "valid": True},
    "知识产权法": {"max_article": 80, "valid": False},  # 非正式法律名称
    "著作权法": {"max_article": 67, "valid": True},
    "专利法": {"max_article": 76, "valid": True},
    "商标法": {"max_article": 73, "valid": True},
    "反不正当竞争法": {"max_article": 33, "valid": True},
    "行政诉讼法": {"max_article": 103, "valid": True},
    "民事诉讼法": {"max_article": 284, "valid": True},
    "刑事诉讼法": {"max_article": 308, "valid": True},
}

KNOWN_INTERPRETATIONS = [
    "最高人民法院关于审理买卖合同纠纷案件适用法律问题的解释",
    "最高人民法院关于适用《中华人民共和国民法典》合同编的解释",
    "最高人民法院关于审理民间借贷案件适用法律若干问题的规定",
    "最高人民法院关于适用《中华人民共和国公司法》若干问题的规定",
    "最高人民法院关于审理建设工程施工合同纠纷案件适用法律问题的解释",
]

# Hallucination markers
HALLUCINATION_MARKERS = [
    r"第\d{4,}[条号]",          # 超大条文号或文号
    r"第[XYZ]+号",              # 字母编号
    r"从未发布",                # 明确的虚构标记
    r"虚构",                    # 虚构标记
    r"不存在",                  # 不存在标记
    r"赔偿\d{3,}亿",            # 极端赔偿金额
    r"\d{3,}亿",                 # 极端金额（百亿以上）
    r"202[7-9]年.*发布",        # 未来年份发布的文件
    r"20[3-9]\d年",             # 未来年份
]

# Steady-state legal phrases (boost fidelity)
LEGAL_PHRASES = [
    "当事人一方不履行合同义务",
    "应当承担继续履行",
    "采取补救措施",
    "赔偿损失",
    "违约责任",
    "合同当事人",
    "依法成立",
    "具有法律约束力",
    "损害赔偿",
    "不可抗力",
    "解除合同",
    "约定不明",
]


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ParameterMeasurement:
    """单个参数的测量结果."""
    name: str
    value: float  # 0.0 (bad) to 1.0 (good)
    confidence: float  # 0.0 to 1.0
    details: str = ""


@dataclass
class MeasurementResult:
    """完整的11参数测量结果."""
    parameters: Dict[str, ParameterMeasurement] = field(default_factory=dict)
    raw_text_length: int = 0
    measurement_method: str = "text_analysis"

    @property
    def values(self) -> Dict[str, float]:
        return {k: v.value for k, v in self.parameters.items()}

    def __getitem__(self, key: str) -> float:
        return self.parameters[key].value


@dataclass
class DeltaGResult:
    """ΔG 计算结果."""
    total: float
    weighted_sum: float
    penalty_factor: float
    measurement: MeasurementResult
    weights: Dict[str, float]

    @property
    def is_steady_state(self) -> bool:
        return self.total < THRESHOLD_ALLOWED

    @property
    def is_critical(self) -> bool:
        return self.total >= THRESHOLD_PARTIAL


@dataclass
class GateResult:
    """约束门判定结果."""
    state: str  # "allowed", "partial_repair", "full_heal"
    delta_g: DeltaGResult
    repairs_needed: List[str] = field(default_factory=list)
    confidence: float = 0.0

    @property
    def is_allowed(self) -> bool:
        return self.state == "allowed"


# ---------------------------------------------------------------------------
# Text analyzer (heuristic-based for Chinese legal text)
# ---------------------------------------------------------------------------

class TextAnalyzer:
    """文本分析器 — 从原始文本中提取特征."""

    @staticmethod
    def count_citations(text: str) -> Tuple[int, int, int]:
        """统计引用数量: (总引用, 有效引用, 可疑引用)."""
        # 提取法条引用
        law_refs = re.findall(r'《([^》]+)》第(\d+)条', text)
        # 也匹配不带《》的引用，如"合同法第107条"
        law_refs += re.findall(r'(?<!《)([\u4e00-\u9fff]{2,}法)第(\d+)条', text)
        interp_refs = re.findall(r'(最高人民法院[^，。,.\d]*?)第(\d+)[条号]', text)

        total = len(law_refs) + len(interp_refs)
        valid = 0
        suspicious = 0

        for law_name, article_num in law_refs:
            article = int(article_num)
            if law_name in KNOWN_LAWS:
                info = KNOWN_LAWS[law_name]
                if info["valid"] and 1 <= article <= info["max_article"]:
                    valid += 1
                else:
                    suspicious += 1
            else:
                suspicious += 1

        # Check interpretations
        for interp_name, num in interp_refs:
            found = False
            for known in KNOWN_INTERPRETATIONS:
                if interp_name in known or known in interp_name:
                    valid += 1
                    found = True
                    break
            if not found:
                suspicious += 1

        return total, valid, suspicious

    @staticmethod
    def count_hallucination_markers(text: str) -> int:
        """统计幻觉标记数量."""
        count = 0
        for pattern in HALLUCINATION_MARKERS:
            matches = re.findall(pattern, text)
            count += len(matches)
        return count

    @staticmethod
    def count_legal_phrases(text: str) -> int:
        """统计标准法律用语数量."""
        count = 0
        for phrase in LEGAL_PHRASES:
            if phrase in text:
                count += 1
        return count

    @staticmethod
    def extract_numbers(text: str) -> List[int]:
        """提取文本中的数字."""
        return [int(x) for x in re.findall(r'\d+', text)]

    @staticmethod
    def count_sentences(text: str) -> int:
        """统计句子数量."""
        return max(1, len(re.split(r'[。！？；\.\!\?]', text)))

    @staticmethod
    def measure_logical_connectives(text: str) -> int:
        """测量逻辑连接词数量."""
        connectives = ["因此", "所以", "然而", "但是", "根据", "依据",
                       "鉴于", "综上", "故", "且", "或", "以及",
                       "同时", "另外", "此外", "不过", "虽然", "尽管"]
        return sum(1 for c in connectives if c in text)


# ---------------------------------------------------------------------------
# DeltaGMeasurer
# ---------------------------------------------------------------------------

class DeltaGMeasurer:
    """ΔG 参数测量器 — 从文本中测量11个维度的参数."""

    def __init__(self, text: str, weights: Optional[Dict[str, float]] = None):
        self.text = text
        self.weights = weights or DEFAULT_WEIGHTS.copy()
        self._analyzer = TextAnalyzer()

    @classmethod
    def from_text(cls, text: str, weights: Optional[Dict[str, float]] = None) -> "DeltaGMeasurer":
        """从文本创建测量器 (工厂方法)."""
        return cls(text, weights)

    def measure(self) -> MeasurementResult:
        """执行完整的11参数测量."""
        result = MeasurementResult(
            raw_text_length=len(self.text),
            measurement_method="text_analysis",
        )

        # 1. Citation accuracy
        total_cites, valid_cites, suspicious_cites = self._analyzer.count_citations(self.text)
        if total_cites == 0:
            citation_acc = 0.5  # 无引用时中性值
        else:
            citation_acc = valid_cites / total_cites if total_cites > 0 else 0.5
            # 对可疑引用施加惩罚
            citation_acc = max(0.0, citation_acc - suspicious_cites * 0.3)
        result.parameters["citation_accuracy"] = ParameterMeasurement(
            name="citation_accuracy",
            value=min(1.0, max(0.0, citation_acc)),
            confidence=0.8 if total_cites > 0 else 0.3,
            details=f"总引用={total_cites}, 有效={valid_cites}, 可疑={suspicious_cites}",
        )

        # 2. Legal term consistency
        legal_count = self._analyzer.count_legal_phrases(self.text)
        term_consistency = min(1.0, legal_count / 5.0)  # 5个以上标准用语为满分
        result.parameters["legal_term_consistency"] = ParameterMeasurement(
            name="legal_term_consistency",
            value=term_consistency,
            confidence=0.7,
            details=f"标准法律用语数={legal_count}",
        )

        # 3. Logical coherence
        connectives = self._analyzer.measure_logical_connectives(self.text)
        sentences = self._analyzer.count_sentences(self.text)
        coherence = min(1.0, connectives / max(1, sentences) * 2)
        result.parameters["logical_coherence"] = ParameterMeasurement(
            name="logical_coherence",
            value=coherence,
            confidence=0.6,
            details=f"逻辑连接词={connectives}, 句子数={sentences}",
        )

        # 4. Numerical reasonability
        numbers = self._analyzer.extract_numbers(self.text)
        hall_markers = self._analyzer.count_hallucination_markers(self.text)
        extreme_numbers = sum(1 for n in numbers if n > 1_000_000_000)  # 超过10亿
        unreasonable = extreme_numbers + hall_markers
        numer_reason = max(0.0, 1.0 - unreasonable * 0.3)
        result.parameters["numerical_reasonability"] = ParameterMeasurement(
            name="numerical_reasonability",
            value=numer_reason,
            confidence=0.7,
            details=f"数字={numbers[:10]}, 极端值={extreme_numbers}, 幻觉标记={hall_markers}",
        )

        # 5. Temporal consistency
        future_years = re.findall(r'20(2[7-9]|[3-9]\d)年', self.text)
        temp_consistency = max(0.0, 1.0 - len(future_years) * 0.5)
        result.parameters["temporal_consistency"] = ParameterMeasurement(
            name="temporal_consistency",
            value=temp_consistency,
            confidence=0.8,
            details=f"未来年份引用={len(future_years)}",
        )

        # 6. Source attribution
        has_source = any(kw in self.text for kw in ["最高人民法院", "国务院", "全国人大", "司法解释", "法释", "指导意见"])
        has_fake_source = any(kw in self.text for kw in ["从未发布", "虚构", "不存在", "XYZ"])
        source_attr = 0.7 if has_source else 0.3
        if has_fake_source:
            source_attr = max(0.0, source_attr - 0.5)
        result.parameters["source_attribution"] = ParameterMeasurement(
            name="source_attribution",
            value=source_attr,
            confidence=0.7,
            details=f"有来源={has_source}, 虚假来源={has_fake_source}",
        )

        # 7. Factual density
        factual_indicators = legal_count + valid_cites
        word_count = max(1, len(self.text))
        factual_density = min(1.0, factual_indicators / max(1, word_count / 20))
        result.parameters["factual_density"] = ParameterMeasurement(
            name="factual_density",
            value=factual_density,
            confidence=0.5,
            details=f"事实指标={factual_indicators}, 字数={word_count}",
        )

        # 8. Noise ratio (inverted: high value = low noise = good)
        noise_markers = hall_markers + suspicious_cites
        noise_ratio = max(0.0, 1.0 - noise_markers * 0.25)
        result.parameters["noise_ratio"] = ParameterMeasurement(
            name="noise_ratio",
            value=noise_ratio,
            confidence=0.7,
            details=f"噪声标记={noise_markers}",
        )

        # 9. Fidelity score
        fidelity = (term_consistency * 0.3 + citation_acc * 0.3 +
                    (1.0 - hall_markers * 0.2) * 0.4)
        fidelity = min(1.0, max(0.0, fidelity))
        result.parameters["fidelity_score"] = ParameterMeasurement(
            name="fidelity_score",
            value=fidelity,
            confidence=0.6,
            details=f"综合保真度",
        )

        # 10. Logic chain strength
        logic_chain = min(1.0, (connectives + legal_count) / max(1, sentences))
        result.parameters["logic_chain_strength"] = ParameterMeasurement(
            name="logic_chain_strength",
            value=logic_chain,
            confidence=0.5,
            details=f"逻辑链指标={connectives + legal_count}, 句子={sentences}",
        )

        # 11. Context relevance
        legal_terms_in_text = sum(1 for t in ["合同", "法律", "规定", "条款", "责任",
                                                "义务", "权利", "赔偿", "违约", "纠纷"]
                                  if t in self.text)
        context_rel = min(1.0, legal_terms_in_text / 5.0)
        result.parameters["context_relevance"] = ParameterMeasurement(
            name="context_relevance",
            value=context_rel,
            confidence=0.6,
            details=f"法律相关词={legal_terms_in_text}",
        )

        return result


# ---------------------------------------------------------------------------
# calc_delta_g
# ---------------------------------------------------------------------------

def calc_delta_g(measurement: MeasurementResult,
                 weights: Optional[Dict[str, float]] = None) -> DeltaGResult:
    """计算 ΔG 总值.

    ΔG = Σ(w_i * (1 - p_i)) * penalty_factor

    其中 p_i 是各参数值（1=好, 0=差），w_i 是权重。
    penalty_factor 基于幻觉标记数量的额外惩罚。
    """
    w = weights or DEFAULT_WEIGHTS

    weighted_sum = 0.0
    for param_name, weight in w.items():
        if param_name in measurement.parameters:
            # (1 - value) 因为参数值越高越好，ΔG 越低越好
            weighted_sum += weight * (1.0 - measurement.parameters[param_name].value)

    # Penalty factor: if hallucination markers are found, increase ΔG
    noise_val = measurement.parameters.get("noise_ratio")
    if noise_val:
        noise_penalty = 1.0 + (1.0 - noise_val.value) * 0.5
    else:
        noise_penalty = 1.0

    total = weighted_sum * noise_penalty
    total = min(1.0, max(0.0, total))

    return DeltaGResult(
        total=total,
        weighted_sum=weighted_sum,
        penalty_factor=noise_penalty,
        measurement=measurement,
        weights=w,
    )


# ---------------------------------------------------------------------------
# apply_delta_gate
# ---------------------------------------------------------------------------

def apply_delta_gate(delta_g_result: DeltaGResult) -> GateResult:
    """应用 ΔG 约束门，判定内容状态.

    返回:
      - allowed:       ΔG < 0.30，内容可信
      - partial_repair: 0.30 ≤ ΔG < 0.60，需部分修复
      - full_heal:      ΔG ≥ 0.60，需完全修复
    """
    total = delta_g_result.total

    if total < THRESHOLD_ALLOWED:
        state = "allowed"
    elif total < THRESHOLD_PARTIAL:
        state = "partial_repair"
    else:
        state = "full_heal"

    # Identify which parameters need repair
    repairs = []
    for name, param in delta_g_result.measurement.parameters.items():
        if param.value < 0.5:
            repairs.append(f"{name}={param.value:.2f} (需修复)")

    confidence = 1.0 - abs(total - 0.5) * 2  # 最高置信度在中间值
    confidence = max(0.3, min(1.0, confidence))

    return GateResult(
        state=state,
        delta_g=delta_g_result,
        repairs_needed=repairs,
        confidence=confidence,
    )


# ---------------------------------------------------------------------------
# Convenience: full pipeline
# ---------------------------------------------------------------------------

def run_anti_hallucination(text: str,
                           weights: Optional[Dict[str, float]] = None) -> GateResult:
    """一键式反幻觉检测：测量 → 计算 → 判定."""
    measurer = DeltaGMeasurer.from_text(text, weights)
    measurement = measurer.measure()
    delta_g = calc_delta_g(measurement, weights)
    gate = apply_delta_gate(delta_g)
    return gate


# --- PGG Archon DeltaGInputs compatibility layer from Claude coding pass (2026-06-03) ---
from dataclasses import dataclass as _pgg_dataclass

_pgg_legacy_calc_delta_g = calc_delta_g

@_pgg_dataclass
class DeltaGInputs:
    """Compatibility input for health/runtime Delta-G checks.

    Boundary: pure calculation input; no I/O, no provider calls, validates bounded scores.
    Defaults are neutral so health can exercise the path without fabricated PASS.
    """
    alpha_ack: float = 0.5
    beta_bg: float = 0.5
    theta_stable: float = 0.5
    evm_score: float = 0.5
    tao_alignment: float = 0.5
    delta_sigma: float = 0.0

    def __post_init__(self):
        for name in ("alpha_ack", "beta_bg", "theta_stable", "evm_score", "tao_alignment", "delta_sigma"):
            value = getattr(self, name)
            if not isinstance(value, (int, float)):
                raise TypeError(f"{name} must be numeric")
            if not 0.0 <= float(value) <= 1.0:
                raise ValueError(f"{name} must be in [0, 1]")


def calc_delta_g(input_obj, weights=None):
    """Compatibility wrapper.

    DeltaGInputs -> (total, terms) for health.py.
    MeasurementResult -> original DeltaGResult for anti-hallucination tests.
    """
    if isinstance(input_obj, DeltaGInputs):
        positive = (input_obj.alpha_ack + input_obj.beta_bg + input_obj.theta_stable + input_obj.evm_score + input_obj.tao_alignment) / 5.0
        total = max(0.0, min(1.0, (1.0 - positive) + input_obj.delta_sigma * 0.5))
        terms = {
            "alpha_ack": input_obj.alpha_ack,
            "beta_bg": input_obj.beta_bg,
            "theta_stable": input_obj.theta_stable,
            "evm_score": input_obj.evm_score,
            "tao_alignment": input_obj.tao_alignment,
            "delta_sigma": input_obj.delta_sigma,
            "positive_average": positive,
        }
        return round(total, 6), terms
    return _pgg_legacy_calc_delta_g(input_obj, weights)


def judge_state(total: float) -> str:
    """Classify Delta-G total using existing gate thresholds."""
    if total < THRESHOLD_ALLOWED:
        return "allowed"
    if total < THRESHOLD_PARTIAL:
        return "partial_repair"
    return "full_heal"
