"""策略提取器 - 从基因中提取优质策略"""
from typing import Dict, List, Optional


class StrategyExtractor:
    """从基因中提取可复用的策略"""
    
    def extract(self, gene: Dict) -> Dict:
        """提取基因中的策略"""
        return {
            'name': gene.get('name', 'unknown'),
            'strategy': gene.get('strategy', gene.get('description', '')),
            'fitness': gene.get('fitness', 0.0),
            'parameters': gene.get('parameters', {}),
            'patterns': gene.get('patterns', [])
        }
    
    def extract_all(self, genes: List[Dict]) -> List[Dict]:
        """批量提取"""
        return [self.extract(g) for g in genes]
