# GeneNexus

> 璇玑基因枢纽 · 智能体进化熔炉

**GeneNexus** — 连接璇玑基因库与智能体SKILL的枢纽

---

## 核心定位

解决璇玑基因无法直接注入智能体的难题：
```
璇玑基因库 → GeneNexus → SKILL格式 → 墨羽学会
```

---

## 核心公式

```
Φ_learn = Gene_Strategy × SKILL_Format × Memory_Integration

Φ_gene = (C_gene × Λ_selection × Ω_fitness) / (H_noise × t_learn)
```

---

## 工作流程

```
┌─────────────────┐
│  璇玑基因库     │
│  /nvm/assets/   │
└────────┬────────┘
         │ GeneNexus读取
         ▼
┌─────────────────┐
│  策略提取器     │
│  strategy_      │
│  extractor.py   │
└────────┬────────┘
         │ 策略格式化
         ▼
┌─────────────────┐
│  SKILL生成器    │
│  skill_generator│
│  .py            │
└────────┬────────┘
         │ 墨羽学习
         ▼
┌─────────────────┐
│  墨羽技能库     │
│  SKILL/        │
└─────────────────┘
```

---

## 核心模块

### 1. 基因读取器
```python
from gene_nexus import GeneReader

reader = GeneReader("/root/.nvm/assets/gep/genes.json")
genes = reader.load_genes()
print(f"加载 {len(genes)} 个基因")
```

### 2. 策略提取器
```python
from gene_nexus import StrategyExtractor

extractor = StrategyExtractor()
for gene in genes:
    strategy = extractor.extract(gene)
    print(f"策略: {strategy}")
```

### 3. SKILL生成器
```python
from gene_nexus import SkillGenerator

generator = SkillGenerator()
skill = generator.generate(strategy)
print(f"SKILL: {skill.name}")
```

---

## 安装

```bash
git clone https://github.com/ApexSpiral/GeneNexus.git
cd GeneNexus
pip install -r requirements.txt
```

---

## 使用

```bash
# 完整流程
python -m gene_nexus --mode full

# 仅提取策略
python -m gene_nexus --mode extract

# 仅生成SKILL
python -m gene_nexus --mode generate
```

---

## 测试

```bash
pytest tests/ -v
```

---

## 项目特点

- ✅ 真实Python实现，无模拟
- ✅ 连接璇玑基因与墨羽SKILL
- ✅ 自动提取优质策略
- ✅ 标准化SKILL格式输出

---

## 适用场景

- 璇玑基因库策略复用
- 智能体技能自动扩充
- 优质编码经验沉淀
- 进化经验传承

---

## License

MIT
