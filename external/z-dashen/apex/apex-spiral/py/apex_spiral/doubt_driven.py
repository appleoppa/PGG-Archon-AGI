"""
APEX Doubt-Driven Development Module
融合addyosmani/agent-skills doubt-driven-development × APEX Γ维度

APEX Γ(博弈) = 多Agent竞争博弈
Doubt-Driven = 质疑驱动开发，非trivial决策必须经过对抗性审查

Author: 璇玑帝国
"""

from dataclasses import dataclass, field
from typing import Optional, List, Callable
from enum import Enum
import json


class DoubtLevel(Enum):
    """Doubt驱动级别"""
    TRIVIAL = "trivial"           # 机械操作，跳过doubt
    NON_TRIVIAL = "non-trivial"  # 需要doubt审查
    HIGH_STAKES = "high-stakes"  # 高风险，需要交叉审查


@dataclass
class Claim:
    """决策声明"""
    statement: str
    why_matters: str
    artifact: str
    contract: str
    stake_level: DoubtLevel = DoubtLevel.NON_TRIVIAL


@dataclass
class DoubtFinding:
    """质疑发现"""
    finding_type: str  # contract_misread / valid_actionable / valid_tradeoff / noise
    description: str
    artifact_reference: str
    action_required: Optional[str] = None


@dataclass
class DoubtCycle:
    """完整doubt循环"""
    claim: Claim
    findings: List[DoubtFinding] = field(default_factory=list)
    cycle_count: int = 0
    stop_reason: Optional[str] = None
    cross_model_offered: bool = False
    cross_model_used: bool = False


class APEXDoubtEngine:
    """
    APEX Γ维度 - Doubt-Driven开发引擎
    
    融合doubt-driven-development五步法与APEX博弈论：
    - CLAIM: 显式声明决策
    - EXTRACT: 提取最小审查单元
    - DOUBT: 对抗性审查
    - RECONCILE: 分类整理发现
    - STOP: 停止条件
    """
    
    def __init__(self, gamma: float = 0.29):
        """
        初始化Doubt引擎
        
        Args:
            gamma: APEX Γ值，默认0.29（多Agent博弈基线）
        """
        self.gamma = gamma
        self.cycles: List[DoubtCycle] = []
        self.tradeoff_log: List[DoubtFinding] = []
        
    def is_non_trivial(self, 
                       introduces_branching: bool = False,
                       crosses_boundary: bool = False,
                       types_unverifiable: bool = False,
                       context_dependent: bool = False,
                       irreversible: bool = False) -> bool:
        """判断是否non-trivial"""
        return (introduces_branching or crosses_boundary or 
                types_unverifiable or context_dependent or irreversible)
    
    def classify_finding(self, finding: str, artifact: str, contract: str) -> DoubtFinding:
        """
        分类质疑发现（RECONCILE步骤）
        
        优先级顺序：
        1. contract_misread - 契约本身问题
        2. valid_actionable - 真实问题，需修改
        3. valid_tradeoff - 真实权衡，接受
        4. noise - 误报
        """
        # 简化分类逻辑
        if "convention" in finding.lower() or "context" in finding.lower():
            return DoubtFinding(
                finding_type="noise",
                description=finding,
                artifact_reference=artifact[:100]
            )
        elif "risk" in finding.lower() or "error" in finding.lower():
            return DoubtFinding(
                finding_type="valid_actionable",
                description=finding,
                artifact_reference=artifact[:100],
                action_required="需修复"
            )
        else:
            return DoubtFinding(
                finding_type="valid_tradeoff",
                description=finding,
                artifact_reference=artifact[:100]
            )
    
    def run_doubt_cycle(self, 
                        claim: Claim,
                        review_func: Callable[[str, str], List[str]]) -> DoubtCycle:
        """
        运行完整doubt循环
        
        Args:
            claim: 决策声明
            review_func: 审查函数，输入(artifact, contract)，返回问题列表
        
        Returns:
            DoubtCycle: 完整循环结果
        """
        cycle = DoubtCycle(claim=claim)
        
        # 步骤1: CLAIM - 已在claim中
        print(f"[Doubt] CLAIM: {claim.statement}")
        
        # 步骤2: EXTRACT - 提取最小单元
        artifact = claim.artifact
        contract = claim.contract
        print(f"[Doubt] EXTRACT: artifact长度={len(artifact)}, contract长度={len(contract)}")
        
        # 步骤3: DOUBT - 对抗性审查
        max_cycles = 3
        for i in range(max_cycles):
            cycle.cycle_count += 1
            issues = review_func(artifact, contract)
            
            print(f"[Doubt] Cycle {cycle.cycle_count}: 发现{len(issues)}个问题")
            
            # 分类发现
            for issue in issues:
                finding = self.classify_finding(issue, artifact, contract)
                cycle.findings.append(finding)
                
                if finding.finding_type == "valid_actionable":
                    print(f"  ⚠️ {issue[:80]}")
                elif finding.finding_type == "valid_tradeoff":
                    print(f"  ⚖️ {issue[:80]}")
                else:
                    print(f"  ✓ {issue[:80]}")
            
            # 停止条件检查
            if not issues or all(f.finding_type == "noise" for f in cycle.findings[-len(issues):]):
                cycle.stop_reason = "trivial_findings"
                print(f"[Doubt] STOP: 仅trivial发现")
                break
                
            if cycle.cycle_count >= max_cycles:
                cycle.stop_reason = "max_cycles"
                print(f"[Doubt] STOP: 达到{max_cycles}轮上限")
                break
        
        # 记录tradeoff
        for f in cycle.findings:
            if f.finding_type == "valid_tradeoff":
                self.tradeoff_log.append(f)
        
        return cycle
    
    def gamma_adjust(self) -> float:
        """
        根据doubt表现调整Γ值
        
        严格审查 → Γ提升
        宽松放过 → Γ下降
        """
        if not self.cycles:
            return self.gamma
        
        # 计算actionable比例
        total = sum(len(c.findings) for c in self.cycles)
        if total == 0:
            return self.gamma * 0.95  # 没有发现问题，降低Γ
        
        actionable = sum(1 for c in self.cycles 
                        for f in c.findings 
                        if f.finding_type == "valid_actionable")
        
        strictness = actionable / total if total > 0 else 0
        
        # 严格度调整Γ
        new_gamma = self.gamma * (1 + strictness * 0.2)
        new_gamma = min(max(new_gamma, 0.1), 1.0)  # 限制范围
        
        print(f"[Γ调整] {self.gamma:.3f} → {new_gamma:.3f} (严格度={strictness:.2f})")
        self.gamma = new_gamma
        return new_gamma


def create_adversarial_prompt(artifact: str, contract: str) -> str:
    """
    创建对抗性审查prompt
    
    Args:
        artifact: 代码/决策内容
        contract: 契约/规格说明
    
    Returns:
        str: 对抗性审查prompt
    """
    return f"""Adversarial review. Find what is wrong with this artifact.
Assume the author is overconfident. Look for:
- Unstated assumptions
- Edge cases not handled
- Hidden coupling or shared state
- Ways the contract could be violated
- Existing conventions this might break
- Failure modes under unexpected input

Do NOT validate. Do NOT summarize. Find issues, or state
explicitly that you cannot find any after thorough examination.

ARTIFACT:
{artifact}

CONTRACT:
{contract}"""


def example_review(artifact: str, contract: str) -> List[str]:
    """示例审查函数（实际使用时替换为真实LLM调用）"""
    issues = []
    
    # 模拟对抗性审查
    if "race" in artifact.lower() or "concurrent" in artifact.lower():
        issues.append("Thread safety not verified - race condition possible")
    
    if "cache" in artifact.lower():
        issues.append("Cache invalidation strategy unclear")
    
    if len(artifact) > 500:
        issues.append("Artifact too large - should be decomposed")
    
    return issues


# 导出快捷函数
def doubt_decision(statement: str, 
                   why: str, 
                   artifact: str, 
                   contract: str,
                   review_func: callable = example_review) -> DoubtCycle:
    """
    快捷doubt决策函数
    
    用法:
        cycle = doubt_decision(
            statement="缓存层是线程安全的",
            why="竞态条件会损坏用户数据",
            artifact=caching_code,
            contract="read-heavy workload下的线程安全",
            review_func=my_llm_review
        )
    """
    engine = APEXDoubtEngine()
    claim = Claim(
        statement=statement,
        why_matters=why,
        artifact=artifact,
        contract=contract
    )
    return engine.run_doubt_cycle(claim, review_func)


if __name__ == "__main__":
    # 示例
    sample_code = '''
    def get_user(user_id: str) -> User:
        cache.set(user_id, user_data)  # 潜在竞态
        return cache.get(user_id)
    '''
    
    sample_contract = "返回指定user_id的User对象"
    
    cycle = doubt_decision(
        statement="缓存读取是线程安全的",
        why="多线程环境下竞态条件风险",
        artifact=sample_code,
        contract=sample_contract
    )
    
    print(f"\n结果: {len(cycle.findings)}个发现, 停止原因: {cycle.stop_reason}")
