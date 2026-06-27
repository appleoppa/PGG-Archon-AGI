"""GeneNexus - 璇玑基因枢纽 v1.1
修复：包结构正确，支持 from gene_nexus import GeneReader
"""
from .gene_reader import GeneReader
from .strategy_extractor import StrategyExtractor
from .skill_generator import SkillGenerator

__all__ = ['GeneReader', 'StrategyExtractor', 'SkillGenerator']
__version__ = '1.1.0'
