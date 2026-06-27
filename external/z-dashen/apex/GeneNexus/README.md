# GeneNexus - 璇玑基因枢纽

APEX V10.3 技能演化核心模块。

## 安装
```bash
pip install -e .
```

## 使用
```python
from gene_nexus import GeneReader, StrategyExtractor, SkillGenerator
from gene_nexus.apex_v103_evolver import ApexV103SkillEvolver

# 读取基因
reader = GeneReader()
genes = reader.load_genes()

# 提取策略
extractor = StrategyExtractor()
strategy = extractor.extract(genes[0])

# 生成SKILL
generator = SkillGenerator()
skill = generator.generate(strategy)

# APEX V10.3演化
evolver = ApexV103SkillEvolver()
result = evolver.evolve_skill_with_apex({"signal_strength": 0.8}, 0.7)
```

## v1.1修复
- ✅ 修复包导入问题
- ✅ 添加ApexV103SkillEvolver模块
- ✅ 添加tests测试套件
- ✅ 添加setup.py和pyproject.toml
