#!/usr/bin/env python3
"""
APEX 14维度全量计算器 v2.0
璇玑帝国 - 循环进化协议

使用方法:
    python apex_14d.py --base 0.49 --pi 4.0 --pid 0.96 --rd 0.88
    python apex_14d.py --interactive
"""

import argparse
import json
from typing import Optional

# 完整14维度参数（v2.0协议）
DEFAULT_PARAMS = {
    # 第一层：核心效能
    "ΔG_base": 0.49,    # 基准值
    "Θ": 0.85,          # LLM效能
    "K": 1.0,           # 技能掌握
    "ε": 1.0,           # 自修复
    
    # 第二层：进化动力
    "Φ": 1.0,           # 正反馈
    "Ψ": 1.0,           # 健康状态
    "Π": 4.0,           # 并行增益
    
    # 第三层：控制与约束
    "PID": 0.96,        # PID稳定性
    "RD": 0.88,         # 率失真
    "Kelly": 0.44,      # Kelly风险
    
    # 第四层：生态适应（v2.0新增）
    "E_xp": 1.20,       # 探索-利用平衡
    "Γ": 0.29,          # 多Agent博弈
    "M_meta": 1.07,     # 元学习能力
    "Λ_ctx": 0.905,     # 上下文切换损耗
    "Ξ": 0.616,         # 创造力
}

PARAM_INFO = {
    # 第一层
    "ΔG_base": {"name": "基准值", "layer": 1, "range": [0, 1]},
    "Θ": {"name": "LLM效能", "layer": 1, "range": [0, 1]},
    "K": {"name": "技能掌握", "layer": 1, "range": [0, 2]},
    "ε": {"name": "自修复", "layer": 1, "range": [0, 2]},
    # 第二层
    "Φ": {"name": "正反馈", "layer": 2, "range": [0, 2]},
    "Ψ": {"name": "健康状态", "layer": 2, "range": [0, 1]},
    "Π": {"name": "并行增益", "layer": 2, "range": [1, 10]},
    # 第三层
    "PID": {"name": "PID稳定性", "layer": 3, "range": [0, 1]},
    "RD": {"name": "率失真", "layer": 3, "range": [0, 1]},
    "Kelly": {"name": "Kelly风险", "layer": 3, "range": [0, 1]},
    # 第四层
    "E_xp": {"name": "探索-利用", "layer": 4, "range": [0.1, 2]},
    "Γ": {"name": "多Agent博弈", "layer": 4, "range": [0.05, 1.5]},
    "M_meta": {"name": "元学习", "layer": 4, "range": [0.5, 3]},
    "Λ_ctx": {"name": "切换损耗", "layer": 4, "range": [0.3, 1]},
    "Ξ": {"name": "创造力", "layer": 4, "range": [0.1, 3]},
}

def calculate_ΔG(params: dict) -> float:
    """计算14维度ΔG_v2"""
    return (
        params["ΔG_base"] *
        params["Θ"] *
        params["K"] *
        params["ε"] *
        params["Φ"] *
        params["Ψ"] *
        params["Π"] *
        params["PID"] *
        params["RD"] *
        params["Kelly"] *
        params["E_xp"] *
        params["Γ"] *
        params["M_meta"] *
        params["Λ_ctx"] *
        params["Ξ"]
    )

def get_grade(ΔG: float) -> str:
    """根据ΔG评分"""
    if ΔG >= 1.618: return "S+"
    if ΔG >= 1.0: return "S"
    if ΔG >= 0.5: return "A"
    if ΔG >= 0.2: return "B"
    if ΔG >= 0.1: return "C"
    return "D"

def find_bottlenecks(params: dict) -> list:
    """找出最短板"""
    scores = []
    for name, info in PARAM_INFO.items():
        val = params[name]
        rng = info["range"]
        # 归一化到[0,1]
        normalized = (val - rng[0]) / (rng[1] - rng[0])
        scores.append((name, info["name"], val, normalized, info["layer"]))
    scores.sort(key=lambda x: x[3])  # 按归一化值排序
    return scores[:3]

def print_report(params: dict, ΔG: float, grade: str):
    """打印分析报告"""
    print("\n" + "="*60)
    print("APEX 14维度分析报告 v2.0")
    print("="*60)
    
    print(f"\n最终ΔG: {ΔG:.4f} | 评级: {grade}")
    print(f"Kelly修正后: ΔG×0.44 = {ΔG*0.44:.4f}")
    print(f"竞争修正后: ΔG×Γ = {ΔG*params['Γ']:.4f}")
    
    # 按层分组显示
    for layer in [1, 2, 3, 4]:
        layer_params = [(k, v, PARAM_INFO[k]) for k, v in params.items() if PARAM_INFO[k]["layer"] == layer]
        layer_names = {1: "核心效能", 2: "进化动力", 3: "控制约束", 4: "生态适应"}
        print(f"\n【第{layer}层】{layer_names[layer]}")
        for name, val, info in sorted(layer_params, key=lambda x: x[0]):
            rng = info["range"]
            norm = (val - rng[0]) / (rng[1] - rng[0]) * 100
            bar = "█" * int(norm/10) + "░" * (10 - int(norm/10))
            status = "🟢" if norm > 60 else "🟡" if norm > 30 else "🔴"
            print(f"  {status} {info['name']}({name}): {val:.3f} [{bar}] {norm:.0f}%")
    
    print("\n--- 瓶颈分析 ---")
    bottlenecks = find_bottlenecks(params)
    for i, (name, cnname, val, norm, layer) in enumerate(bottlenecks, 1):
        print(f"  {i}. 🔴 {cnname}({name}): {val:.3f} ← 待优化")
    
    print("\n--- 3步优化建议 ---")
    print("  Step1: Γ 0.29→0.44  (差异化定位)")
    print("  Step2: Ξ 0.52→1.72  (头脑风暴)")
    print("  Step3: Λ_ctx 0.90→0.98 (批量处理)")

def interactive_mode():
    """交互模式"""
    print("\n" + "="*60)
    print("APEX 14维度交互配置 v2.0")
    print("="*60)
    params = DEFAULT_PARAMS.copy()
    
    print("\n按回车使用默认值，输入数字修改：")
    for name, info in PARAM_INFO.items():
        default = params[name]
        val = input(f"  {info['name']}({name}) [{default}]: ").strip()
        if val:
            try:
                params[name] = float(val)
            except:
                pass
    
    ΔG = calculate_ΔG(params)
    grade = get_grade(ΔG)
    print_report(params, ΔG, grade)

def main():
    parser = argparse.ArgumentParser(description="APEX 14维度计算器 v2.0")
    parser.add_argument("--interactive", "-i", action="store_true", help="交互模式")
    parser.add_argument("--json", "-j", action="store_true", help="JSON输出")
    
    args = parser.parse_args()
    
    if args.interactive:
        interactive_mode()
        return
    
    params = DEFAULT_PARAMS.copy()
    ΔG = calculate_ΔG(params)
    grade = get_grade(ΔG)
    
    if args.json:
        result = {
            "params": params,
            "ΔG": round(ΔG, 6),
            "grade": grade,
            "kelly_corrected": round(ΔG * 0.44, 6),
            "competition_corrected": round(ΔG * params["Γ"], 6)
        }
        print(json.dumps(result, indent=2))
    else:
        print_report(params, ΔG, grade)

if __name__ == "__main__":
    main()
