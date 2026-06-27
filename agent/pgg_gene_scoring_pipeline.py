"""PGG Gene Scoring Pipeline v1.0 — Batch-score unscored candidate genes.

Scoring heuristics (0-100 scale):
  - Source repo quality: known orgs (80-100), personal repos (30-60), local files (10-30)
  - Pattern type sophistication: multi_llm/evolution/architecture high, simple=low
  - Code snippet content: lines of code, presence of tests, docstrings
  - Name bonus: well-named genes (+5-10)

Boundary: heuristic static scoring only; no LLM calls, no network.
"""
import json, sqlite3, re, time
from pathlib import Path
from urllib.parse import urlparse

DB_PATH = Path.home() / '.hermes' / 'data' / 'pgg_archon.db'
MIN_SCORE_TO_KEEP = 10

HIGH_QUALITY_ORGS = {
    'openai', 'anthropic', 'google', 'meta', 'microsoft', 'nvidia',
    'huggingface', 'NousResearch', 'stanfordnlp', 'deepmind',
    'THU', 'PKU', 'tsinghua', 'mit', 'berkeley',
    'pytorch', 'tensorflow', 'langchain', 'llama',
    'appleoppa/pgg-archon', 'appleoppa/pgg', 'NousResearch/hermes-agent',
}
MEDIUM_QUALITY_ORGS = {
    'appleoppa', 'github', 'anthropics', 'GradientJ', 'Human-Agent-Society',
    'dair-ai', 'ml-explore', 'EliteFriendly', 'szemyd', 'ApexSpiral',
    'OpenBMB', 'meta-llama', 'deepseek-ai',
}


def _github_owner_repo(repo: str) -> tuple[str, str, bool]:
    """Return (owner, owner/repo, is_github_host) after parsing the repo URL.

    CodeQL correctly flags raw substring checks such as ``"github.com/" in url``.
    This helper parses host/path first and only treats an input as GitHub when
    the hostname is exactly ``github.com`` (or ``www.github.com``).
    """
    raw = (repo or '').strip()
    if not raw:
        return '', '', False
    candidate = raw if '://' in raw else f'https://{raw}'
    parsed = urlparse(candidate)
    host = (parsed.hostname or '').lower()
    is_github = host in {'github.com', 'www.github.com'}
    if not is_github:
        return '', '', False
    parts = [p for p in parsed.path.split('/') if p]
    owner = parts[0].lower() if parts else ''
    full = f'{owner}/{parts[1].lower()}' if len(parts) >= 2 else owner
    return owner, full, True


def _repo_tokens(repo: str) -> set[str]:
    return {t for t in re.split(r'[^a-z0-9_.-]+', (repo or '').lower()) if t}

def _repo_score(repo: str) -> int:
    if not repo:
        return 10
    repo_lower = repo.lower()
    if repo_lower.startswith('local') or '~/' in repo_lower:
        return 20
    owner, full_repo, is_github = _github_owner_repo(repo)
    parsed_raw = urlparse(repo) if '://' in repo else urlparse('')
    external_non_github = bool(parsed_raw.scheme and parsed_raw.hostname and (parsed_raw.hostname or '').lower() not in {'github.com', 'www.github.com'})
    tokens = set() if external_non_github else _repo_tokens(repo)
    for org in HIGH_QUALITY_ORGS:
        org_l = org.lower()
        if org_l == owner or org_l == full_repo or org_l in tokens:
            return 90
    for org in MEDIUM_QUALITY_ORGS:
        org_l = org.lower()
        if org_l == owner or org_l == full_repo or org_l in tokens:
            return 60
    if is_github:
        return 40
    if 'hermes' in tokens or 'pgg' in tokens or 'archon' in tokens:
        return 50
    return 25

def _pattern_score(pattern_type: str) -> int:
    pattern = (pattern_type or '').lower()
    HIGH = ['multi_llm', 'evolution', 'gene', 'evolver', 'apex', 'agi',
            'bridge', 'gate', 'architecture', 'self_improve', 'meta']
    MEDIUM = ['agent', 'workflow', 'orchestrator', 'pipeline', 'multi_agent',
              'reactor', 'sidecar', 'gateway', 'router', 'debate',
              'llm', 'reasoning', 'training', 'mcp']
    LOW = ['tool', 'util', 'helper', 'base', 'template', 'daemon',
           'hook', 'plugin', 'adapter', 'cli', 'embedding', 'store']
    for p in HIGH:
        if p in pattern:
            return 85
    for p in MEDIUM:
        if p in pattern:
            return 60
    for p in LOW:
        if p in pattern:
            return 35
    return 40

def _code_score(code_snippet: str) -> int:
    if not code_snippet:
        return 0
    lines = code_snippet.strip().split('\n')
    loc = len(lines)
    if loc < 3:
        return 5
    if loc > 100:
        return 60
    if loc > 50:
        return 50
    if loc > 20:
        return 35
    return 20

def _name_bonus(name: str) -> int:
    name_lower = (name or '').lower()
    bonus = 0
    if len(name) > 15:
        bonus += 5
    if re.search(r'v\d|_\d|_final', name_lower):
        bonus += 5
    return bonus

def score_gene(name: str, pattern_type: str, source_repo: str, code_snippet: str) -> dict:
    r_repo = _repo_score(source_repo)
    r_pattern = _pattern_score(pattern_type)
    r_code = _code_score(code_snippet)
    r_name = _name_bonus(name)
    total = int(r_repo * 0.35 + r_pattern * 0.30 + r_code * 0.25 + r_name * 0.10)
    total = max(0, min(100, total))
    return {'repo_score': r_repo, 'pattern_score': r_pattern,
            'code_score': r_code, 'name_bonus': r_name, 'total': total}

def batch_score() -> dict:
    db = sqlite3.connect(str(DB_PATH))
    c = db.cursor()
    c.execute('SELECT id, name, pattern_type, source_repo, code_snippet FROM genes WHERE quality_score IS NULL OR quality_score <= 1.0')
    unscored = c.fetchall()
    stats = {'scored': 0, 'kept': 0, 'retired': 0}
    for gid, name, ptype, repo, code in unscored:
        result = score_gene(name, ptype, repo, code or '')
        total = result['total']
        if total < MIN_SCORE_TO_KEEP:
            c.execute('UPDATE gene_lifecycle SET state=?, retired_at=? WHERE gene_id=?',
                      ('retired', time.strftime('%Y-%m-%dT%H:%M:%S'), gid))
            c.execute('UPDATE genes SET quality_score=? WHERE id=?', (total, gid))
            stats['retired'] += 1
        else:
            c.execute('UPDATE genes SET quality_score=? WHERE id=?', (total, gid))
            stats['kept'] += 1
        stats['scored'] += 1
    db.commit()
    db.close()
    stats['_boundary'] = 'heuristic static scoring; no LLM calls, no external claims'
    return stats