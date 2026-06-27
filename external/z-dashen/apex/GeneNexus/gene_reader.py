"""璇玑基因读取器 - 真实实现"""
import json
from pathlib import Path
from typing import List, Dict, Optional


class GeneReader:
    """读取璇玑基因库"""
    
    def __init__(self, gene_path: str = "/root/.nvm/assets/gep/genes.json"):
        self.gene_path = Path(gene_path)
    
    def load_genes(self) -> List[Dict]:
        """加载基因库"""
        if not self.gene_path.exists():
            # 尝试备用路径
            alt_paths = [
                "/root/.openclaw/workspace/xuanji_gene/genes.json",
                "./genes.json"
            ]
            for p in alt_paths:
                if Path(p).exists():
                    self.gene_path = Path(p)
                    break
        
        if not self.gene_path.exists():
            return []
        
        with open(self.gene_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if isinstance(data, dict) and 'genes' in data:
            return data['genes']
        elif isinstance(data, list):
            return data
        return []
    
    def get_gene_by_name(self, name: str) -> Optional[Dict]:
        """按名称查找基因"""
        genes = self.load_genes()
        for gene in genes:
            if gene.get('name') == name or name in gene.get('id', ''):
                return gene
        return None
