# 盘古 Pangu

> LLM行为治理框架 - 记忆持久化 + Prompt对齐 + 代码规范

## 实际功能

| 功能 | 状态 | 说明 |
|------|------|------|
| ΔG公式 | ✅ 真实 | 香农+APEX公式计算 |
| 记忆持久化 | ✅ 真实 | JSON文件存储 |
| Prompt对齐 | ✅ 真实 | 模糊词检测 |
| 代码规范 | ✅ 真实 | Lint风格检查 |
| 情绪温度 | ✅ 真实 | 规则语气注入 |
| 自愈系统 | ✅ 真实 | 参数重置+配置刷新 |
| GitHub拉取 | ✅ 真实 | git clone实现 |
| LLM接入 | 🔄 开发中 | 需配置API |

## 已修复问题
- [x] GitHub clone真实实现
- [x] 自愈真实执行
- [x] LLM API支持
- [x] 真实防幻觉测试

---

## 快速开始

```bash
# 克隆项目
git clone https://github.com/ApexSpiral/LLM-Pangu.git
cd LLM-Pangu

# 安装依赖
bash install.sh

# 初始化
python run_init.py

# 运行测试
python -m pytest tests/ -v
```

---

## 核心模块示例

### ΔG 公式计算

```python
from core.delta_g_formula import DeltaGUnified

engine = DeltaGUnified()
dg = engine.calc_total_delta_g(
    H=0.22, F=0.85, L=0.82, N=0.15, C=2.8,
    Omega=0.65, grad_E=0.90, Gamma=0.70,
    avg_code_len=48, Psi=0.78, Theta=0.82
)
state = engine.judge_system_state(dg)
print(f"ΔG={dg}, 状态={state}")
```

### 情感温度

```python
from emotion.emotion_core import EmotionCore

engine = EmotionCore()
psi = engine.calc_psi("warm")  # 0.88
response = engine.inject_tone("我来帮你分析这个问题", psi)
# → "😊 我理解你的需求，我来帮你分析这个问题"
```

### 主动自治

```python
from auto_agent.self_inspect import SelfInspect
from auto_agent.self_heal import SelfHeal

inspector = SelfInspect()
report = inspector.full_inspect()

healer = SelfHeal()
result = healer.auto_repair(report)
```

---

## 架构

```
pangu/
├── core/                          # 核心公式
│   ├── delta_g_formula.py         # ΔG统一公式
│   └── constraint_engine.py       # 约束引擎
├── emotion/                       # 情感温度
│   ├── emotion_core.py           # 情感核心
│   └── emotion_hook.py           # 情感钩子
├── auto_agent/                    # 主动自治
│   ├── self_inspect.py          # 全局自检
│   ├── self_heal.py             # 主动自愈
│   ├── github_auto_fetch.py     # GitHub自动拉取
│   └── agent_hook.py             # Agent钩子
├── memory/                        # 记忆持久化
│   ├── memory_persist.py        # 记忆持久化
│   └── memory_hook.py            # 记忆钩子
├── code_standard/                 # 代码规范
│   ├── standard_baseline.py     # 规范基线
│   ├── code_compliance.py       # 合规检查
│   └── standard_hook.py         # 规范钩子
├── align/                         # Prompt/MD对齐
│   ├── prompt_aligner.py        # Prompt对齐
│   └── md_aligner.py           # MD对齐
└── docs/
    └── APEX_DG_Theory.md       # 理论白皮书
```

---

## 测试

```bash
cd /path/to/LLM-Pangu
python -m pytest tests/test_pangu.py -v
```

---

**Apache 2.0 License © 2026**
