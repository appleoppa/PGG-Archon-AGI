#!/usr/bin/env python3
"""
PGG Daily Learning Pipeline — 多源自主学习闭环
==============================================
每天自动:
  1. GitHub/arXiv/Web 扫 AGI 路线新进展
  2. 抽摘要 → 写候选基因 → 融合 → 反思 → 自愈
  3. 跑本地 benchmark → 分数趋势
  4. 写入 Manifest + 知识沉淀

红线: 不碰 credential/config/security/scheduler/production/full AGI
"""

from __future__ import annotations

import json, os, shutil, sqlite3, subprocess, sys, time, textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HOME = Path.home()
REPO = HOME / ".hermes" / "hermes-agent"
BIN = HOME / ".hermes" / "bin"
DATA = HOME / ".hermes" / "data"
MANIFEST = DATA / "EVOLUTION_MANIFEST.json"
GENE_DB = HOME / ".hermes/workspace/04_knowledge/开智/02-进化基因/apex_evolution_genes.sqlite3"
WORKSPACE_DIR = HOME / ".hermes/workspace/pgg-daily-learning"
HARD_BOUNDARIES = [
    "no_credential_mutation", "no_provider_config_mutation",
    "no_scheduler_security_mutation", "no_production_answer_chain_switch",
    "no_legal_finalization", "no_cross_profile_write",
    "no_memory_apply_without_backup", "no_github_push_without_pr",
]

# ── Helpers ─────────────────────────────────

def _run(cmd: list[str], *, cwd=None, timeout=120) -> dict:
    try:
        cp = subprocess.run(cmd, cwd=str(cwd) if cwd else None,
                           text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           timeout=timeout)
        return {"rc": cp.returncode, "output": cp.stdout}
    except Exception as e:
        return {"rc": 1, "output": f"{type(e).__name__}: {e}"}

def _py() -> str:
    for c in [REPO / ".venv/bin/python3", REPO / "venv/bin/python3", Path(sys.executable)]:
        if c.exists(): return str(c)
    return sys.executable

def _manifest_append(key: str, val: dict) -> None:
    try:
        d = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
        if not isinstance(d, dict): d = {}
        d[key] = val
        MANIFEST.write_text(json.dumps(d, indent=2, default=str))
    except Exception as e:
        print(f"[WARN] manifest: {e}")

# ── Phase 1: 多源学习 ──────────────────────

class MultiSourceLearning:
    """从 GitHub/arXiv/Web 学习 AGI 路线新进展 → 基因候选"""
    
    SOURCES = {
        "github_trending": {
            "name": "GitHub Trending (AGI)",
            "query": "https://api.github.com/search/repositories?q=agi+agent+framework+self-evolution&sort=stars&order=desc&per_page=5",
            "enabled": True,
        },
        "arxiv_recent": {
            "name": "arXiv Recent (AI Agents)",
            "query": "https://export.arxiv.org/api/query?search_query=all:agent+AND+all:self+evolution&start=0&max_results=5&sortBy=submittedDate&sortOrder=descending",
            "enabled": True,
        },
    }
    
    def scan(self) -> list[dict]:
        """Scan all enabled sources → return gene-like items."""
        items = []
        
        # GitHub
        try:
            import urllib.request
            req = urllib.request.Request(
                "https://api.github.com/search/repositories?q=agi+agent+framework+self-evolution&sort=stars&order=desc&per_page=5",
                headers={"Accept": "application/vnd.github.v3+json", "User-Agent": "PGG-Archon"}
            )
            resp = urllib.request.urlopen(req, timeout=30)
            data = json.loads(resp.read())
            for repo in data.get("items", [])[:5]:
                items.append({
                    "type": "github_repo",
                    "source": repo.get("html_url", ""),
                    "name": repo.get("full_name", ""),
                    "description": (repo.get("description") or "")[:200],
                    "stars": repo.get("stargazers_count", 0),
                    "language": repo.get("language", ""),
                    "topics": ",".join(repo.get("topics", [])),
                })
        except Exception as e:
            print(f"  [WARN] GitHub scan: {e}")
        
        # arXiv
        try:
            import urllib.request, xml.etree.ElementTree as ET
            url = "https://export.arxiv.org/api/query?search_query=all:agent+AND+all:self+evolution&start=0&max_results=5&sortBy=submittedDate&sortOrder=descending"
            resp = urllib.request.urlopen(url, timeout=30)
            xml_data = resp.read().decode("utf-8")
            root = ET.fromstring(xml_data)
            ns = {"a": "http://www.w3.org/2005/Atom"}
            for entry in root.findall("a:entry", ns):
                def _t(e: Any, tag: str) -> str:
                    el = e.find(tag, ns)
                    return el.text.strip().replace("\n", " ") if el is not None and el.text else ""
                items.append({
                    "type": "arxiv_paper",
                    "source": _t(entry, "a:id"),
                    "name": _t(entry, "a:title")[:200],
                    "description": _t(entry, "a:summary")[:200],
                    "published": _t(entry, "a:published")[:10],
                })
        except Exception as e:
            print(f"  [WARN] arXiv scan: {e}")
        
        return items
    
    def extract_genes(self, items: list[dict]) -> list[dict]:
        """Extract gene candidates from learning items."""
        genes = []
        for item in items:
            # Simple heuristic: length of description → fitness proxy
            fitness = min(800, 300 + len(item.get("description", "")) * 2)
            genes.append({
                "gene_id": f"pgg_learned_{abs(hash(item.get('source','')) % 10**10):010x}",
                "gate_type": "external_learning",
                "status": "candidate",
                "category": item.get("type", "unknown"),
                "fitness": fitness,
                "content": json.dumps(item),
                "source_url": item.get("source", ""),
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
        return genes


# ── Phase 2: 基因采集 ─────────────────────

def run_gene_intake_pass() -> dict:
    """Run gene intake pipeline (code scan → candidate → fusion → reflexion)."""
    py = _py()
    code = textwrap.dedent("""\
        from agent.pgg_gene_intake_loop import run_intake_loop, gather_reflexion_candidates
        from agent.pgg_archon_gene_fusion_engine import DEFAULT_DB
        import json, sqlite3

        r1 = run_intake_loop(write_candidates=True, top_n=5, db_path=DEFAULT_DB)
        r2 = gather_reflexion_candidates(write=True, db_path=DEFAULT_DB)

        con = sqlite3.connect(DEFAULT_DB)
        total = con.execute('SELECT COUNT(*) FROM evolution_genes').fetchone()[0]
        cand = con.execute("SELECT COUNT(*) FROM evolution_genes WHERE status='candidate'").fetchone()[0]
        ver = con.execute("SELECT COUNT(*) FROM evolution_genes WHERE verification_status LIKE '%verified%'").fetchone()[0]
        reflex = con.execute("SELECT COUNT(*) FROM evolution_genes WHERE gate_type='reflexion_discovery'").fetchone()[0]
        avg_f = con.execute("SELECT AVG(fitness) FROM evolution_genes WHERE fitness IS NOT NULL").fetchone()[0]
        fusion_pass = sum(1 for r in r1.get('fusion_dry_run_results', []) if r.get('fusion_status') == 'PASS')
        con.close()

        print(json.dumps({
            'gene_total': total, 'candidate_count': cand, 'verified_count': ver,
            'reflexion_count': reflex, 'avg_fitness': round(avg_f, 1) if avg_f else 0,
            'fusion_pass': fusion_pass, 'fusion_total': len(r1.get('fusion_dry_run_results', [])),
            'new_intake_written': (r1.get('written_to_genedb') or {}).get('written_count', 0),
            'new_reflexion_written': (r2.get('written_to_genedb') or {}).get('written_count', 0),
            'intake_status': r1.get('status'),
        }))
    """)
    r = _run([py, "-c", code], cwd=REPO, timeout=120)
    if r["rc"] != 0:
        return {"status": "ERROR", "error": r["output"][:300]}
    try:
        return {"status": "PASS", **json.loads(r["output"])}
    except:
        return {"status": "PASS", "output_raw": r["output"][:200]}


# ── Phase 3: 璇玑对齐基因注入 ─────────────

XUANJI_50_STEPS = [
    # 璇玑 35 天路线按微步拆解
    ("SOUL/IDENTITY 对齐", "苹果中枢已有 SOUL.md/USER.md/MEMORY.md", 0.95),
    ("基因融合引擎(加法)", "pgg_archon_gene_fusion_engine.py 已落地", 0.90),
    ("基因融合引擎(乘法)", "归一化乘法已实现", 0.85),
    ("标准基因模板 5层结构", "validate_standard_gene() 已对齐", 0.95),
    ("read_code_to_gene 元能力", "pgg_archon_code_gene_scanner.py + CLI", 0.85),
    ("fitness 追踪", "GeneDB 含 fitness/execution_count 列", 0.90),
    ("自我反思发现管线", "pgg_gene_intake_loop: gather_reflexion_candidates", 0.80),
    ("多源每日学习管线", "本脚本 (pgg_daily_learning_pipeline) 正在建", 0.50),
    ("量子基因 F_quantum", "未实现", 0.0),
    ("L5 觉醒/意识", "PGG 不使用此口径", 0.0),
    ("超能力纪元", "PGG 不宣称超能力状态", 0.0),
    ("AGP 论文吸收", "未逐篇 paper→gene", 0.20),
    ("GEPA 论文吸收", "未逐篇 paper→gene", 0.20),
    ("CORAL 论文吸收", "未逐篇 paper→gene", 0.20),
    ("ML Intern 论文吸收", "未逐篇 paper→gene", 0.20),
    ("Morphogenetic 论文吸收", "未逐篇 paper→gene", 0.20),
    ("SkillEvolver 论文吸收", "未逐篇 paper→gene", 0.20),
    ("APEX-MOSS 论文吸收", "未逐篇 paper→gene", 0.20),
    ("ApexSpiral 基准基因", "未复现/本地评分", 0.10),
    ("基因库 496→1427 增长", "当前 228 vs 1427", 0.16),
    ("每日自愈闭环", "v2.0 自愈管线含基因采集", 0.90),
    ("多LLM 审计门禁", "llm-audit MCP 5模型可用", 0.85),
    ("河图洛书/OmniRoute", "v10.9 固化为6通道路由", 0.95),
    ("EVM 缺陷治理门禁", "evm_runtime_gate 真实证据 (score 0.92)", 0.70),
    ("APEX V10 门禁", "apex_v10_gate (57.14 → 升高证据)", 0.57),
    ("Engineering 公式门禁", "engineering_gate (77.0)", 0.77),
    ("APEXAGI 门禁", "apexagi_gate (73.23)", 0.73),
    ("APEX Core 门禁", "apex_core_gate (92.7)", 0.93),
    ("能力 门禁", "capability_gate (89.25)", 0.89),
    ("Sigma Delta 门禁", "sigma_delta_all (91.42)", 0.91),
    ("本地法律知识库", "SQLite 法规库+指导案例库", 0.90),
    ("EVM 12缺陷治理", "12 defect tracking + runtime evidence", 0.80),
    ("记忆五层治理", "Working/Episodic/Semantic/Procedural/Declarative", 0.85),
    ("神经元系统", "nightly neural consolidation + Akashic", 0.80),
    ("案件 CMS 系统", "cms_case_guard + 部门管线", 0.90),
    ("Rust 核心模块", "PyO3 骨架 + 评估中心", 0.60),
    ("基因 auto-promotion (fitness>900)", "pgg_gene_intake_loop 已实现", 0.85),
    ("融合门禁测试", "4/4 PASS (test_pgg_archon_gene_fusion_engine)", 0.90),
    ("AgentSPEX YAML 规约解析器", "pgg_archon_declarative_spec_parser.py", 0.85),
    ("AgentSPEX W=⟨T,C,P,M,S⟩ 5元组", "spec parser 核心结构", 0.85),
    ("AgentSPEX Step/Control/Parallel 原语", "37 tests PASS", 0.85),
    ("AgentSPEX 执行沙箱", "未实现", 0.0),
    ("AgentSPEX 可视化层", "未实现", 0.0),
    ("AgentSPEX 7项基准", "未实现", 0.0),
    ("本地 mini benchmark", "pgg_local_mini_benchmark.py (27 tests)", 0.80),
    ("公开展示 AI Agent Game 等", "未实现", 0.0),
    ("向量库/检索增强", "法律知识向量库 有, AGI 级无", 0.50),
    ("外部 crowdsource/社区评测", "未连接", 0.0),
    ("持续 vs. 一次性学习", "每日管线正在建，非一次性", 0.45),
    ("APEX 三顺序逻辑执行", "21354/12534/14325 可调用", 0.80),
]

def xuanji_alignment_gene_injection() -> dict:
    """Inject 璇玑 alignment steps as genes into GeneDB, one per gap."""
    gap_items = [s for s in XUANJI_50_STEPS if s[2] < 0.70]
    
    # Write gap genes directly to DB (real schema)
    try:
        con = sqlite3.connect(str(GENE_DB))
        written = 0
        now = datetime.now(timezone.utc).isoformat()
        for name, evidence, score in gap_items:
            gid = f"pgg_xuanji_gap_{abs(hash(name)) % 10**10:010x}"
            content = json.dumps({"name": name, "evidence": evidence, "score": score})
            con.execute(
                """INSERT OR IGNORE INTO evolution_genes
                   (gene_id, gate_type, status, gene_name, absorbed_knowledge,
                    fitness, severity_rank, created_at)
                   VALUES (?, 'xuanji_gap', 'candidate', ?, ?,
                           ?, 3, ?)""",
                (gid, name, content, int(score * 700), now)
            )
            if con.total_changes > 0:
                written += 1
        con.commit()
        con.close()
        return {"status": "PASS", "gap_total": len(gap_items), "written": written,
                "total_alignment_steps": len(XUANJI_50_STEPS)}
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}


# ── Phase 4: 本地 Benchmark ─────────────────

def run_mini_benchmark() -> dict:
    """Run local mini benchmark (if installed)."""
    py = _py()
    bench_path = REPO / "agent" / "pgg_local_mini_benchmark.py"
    if not bench_path.exists():
        return {"status": "SKIP", "reason": "local_mini_benchmark not found"}
    
    r = _run([py, "-c", textwrap.dedent("""\
        from agent.pgg_local_mini_benchmark import run_mini_benchmark
        import json
        result = run_mini_benchmark()
        print(json.dumps(result, indent=2))
    """)], cwd=REPO, timeout=120)
    if r["rc"] != 0:
        return {"status": "ERROR", "error": r["output"][:300]}
    try:
        return {"status": "PASS", "result": json.loads(r["output"])}
    except:
        return {"status": "PASS", "raw": r["output"][:300]}


# ── Phase 5: 报告生成 ─────────────────────

def generate_report(learning_items: list[dict], gene_result: dict,
                    xuanji_result: dict, bench_result: dict) -> dict:
    """Generate daily report → manifest + stdout."""
    ts = datetime.now(timezone.utc).isoformat()
    
    report = {
        "generated_at": ts,
        "learning": {
            "sources_queried": len(MultiSourceLearning.SOURCES),
            "items_found": len(learning_items),
            "genes_extracted": len(learning_items),
        },
        "gene_pipeline": {
            "gene_total": gene_result.get("gene_total", "?"),
            "candidates": gene_result.get("candidate_count", "?"),
            "verified": gene_result.get("verified_count", "?"),
            "reflexion": gene_result.get("reflexion_count", "?"),
            "avg_fitness": gene_result.get("avg_fitness", "?"),
            "fusion_pass": f"{gene_result.get('fusion_pass','?')}/{gene_result.get('fusion_total','?')}",
            "intake_wrote": gene_result.get("new_intake_written", 0),
            "reflexion_wrote": gene_result.get("new_reflexion_written", 0),
        },
        "xuanji_alignment": {
            "steps_total": XUANJI_50_STEPS.__len__(),
            "gaps_found": xuanji_result.get("gap_total", 0),
            "genes_injected": xuanji_result.get("written", 0),
        },
        "benchmark": {
            "status": bench_result.get("status", "?"),
        },
        "boundary": "Daily learning loop. No credential/config/security/production mutation.",
    }
    
    # Write to EVOLUTION_MANIFEST
    key = f"daily_learning_{datetime.now().strftime('%Y%m%d')}"
    _manifest_append(key, report)
    report["manifest_key"] = key
    
    return report


# ── Main ───────────────────────────────────

def main() -> int:
    t0 = time.time()
    WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print(f"PGG Daily Learning Pipeline v1.0")
    print(f"Started: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)
    
    # Phase 1: 多源学习
    print("\n[1/5] 多源学习（GitHub + arXiv）...")
    t1 = time.time()
    learner = MultiSourceLearning()
    items = learner.scan()
    print(f"  找到 {len(items)} 条新发现 | {time.time()-t1:.0f}s")
    for item in items[:3]:
        print(f"    • {item.get('name','?'):<50} {item.get('type','?')}")
    
    # Extract genes from learning
    learned_genes = learner.extract_genes(items)
    learning_write = {"attempted": len(learned_genes), "written": 0, "skipped_existing": 0, "errors": []}
    # Write to GeneDB
    if learned_genes:
        try:
            con = sqlite3.connect(str(GENE_DB))
            now = datetime.now(timezone.utc).isoformat()
            w = 0
            for g in learned_genes:
                before = con.total_changes
                con.execute(
                    """INSERT OR IGNORE INTO evolution_genes
                       (gene_id, gate_type, status, gene_name,
                        fitness, absorbed_knowledge, created_at)
                       VALUES (?, ?, ?, ?,
                               ?, ?, ?)""",
                    (g["gene_id"], g["gate_type"], g["status"], g.get("name", g.get("category", "external")),
                     g["fitness"], g.get("content", ""), g["created_at"])
                )
                if con.total_changes > before:
                    w += 1
                else:
                    learning_write["skipped_existing"] += 1
            con.commit()
            con.close()
            learning_write["written"] = w
            print(f"  写入 GeneDB: {w} 个新基因")
            if w == 0:
                print(f"  [INFO] 外部学习未新增: skipped_existing={learning_write['skipped_existing']}, attempted={learning_write['attempted']}")
        except Exception as e:
            learning_write["errors"].append(str(e)[:240])
            print(f"  [WARN] GeneDB write: {e}")
    else:
        print("  [INFO] 外部学习未新增: no_learning_items_or_no_gene_candidates")
    
    # Phase 2: 基因采集
    print("\n[2/5] 基因采集管线（intake + fusion + reflexion）...")
    t2 = time.time()
    gene_result = run_gene_intake_pass()
    print(f"  {gene_result.get('status','?')} | "
          f"genes={gene_result.get('gene_total','?')}, "
          f"candidates={gene_result.get('candidate_count','?')}, "
          f"fusion={gene_result.get('fusion_pass','?')}/{gene_result.get('fusion_total','?')}, "
          f"avg_fitness={gene_result.get('avg_fitness','?')} | {time.time()-t2:.0f}s")
    
    # Phase 3: 璇玑对齐基因注入
    print("\n[3/5] 璇玑对齐基因注入...")
    t3 = time.time()
    xuanji_result = xuanji_alignment_gene_injection()
    print(f"  {xuanji_result.get('status','?')}: {xuanji_result.get('written',0)} 个缺口基因注入 "
          f"(共 {xuanji_result.get('gap_total',0)}/{xuanji_result.get('total_alignment_steps','?')} 步缺口) | {time.time()-t3:.0f}s")
    
    # Phase 4: Benchmark
    print("\n[4/5] 本地 Benchmark...")
    t4 = time.time()
    bench_result = run_mini_benchmark()
    bench_status = bench_result.get("status", "ERROR")
    if bench_status == "PASS":
        bench_data = bench_result.get("result", bench_result.get("raw", {}))
        if isinstance(bench_data, dict):
            bench_score = bench_data.get("score", bench_data.get("overall", "?"))
        else:
            bench_score = "?"
        print(f"  {bench_status} | score={bench_score} | {time.time()-t4:.0f}s")
    else:
        print(f"  {bench_status}: {bench_result.get('reason', bench_result.get('error', 'unknown'))} | {time.time()-t4:.0f}s")
    
    # Phase 5: 报告
    print("\n[5/5] 报告生成 + Manifest 沉淀...")
    report = generate_report(items, gene_result, xuanji_result, bench_result)
    report["learning"]["write_attempted"] = learning_write.get("attempted", 0)
    report["learning"]["write_inserted"] = learning_write.get("written", 0)
    report["learning"]["write_skipped_existing"] = learning_write.get("skipped_existing", 0)
    report["learning"]["write_errors"] = learning_write.get("errors", [])
    _manifest_append(report["manifest_key"], report)
    print(f"  已写入 manifest: {report.get('manifest_key', '?')}")
    
    # Summary
    print("\n" + "=" * 60)
    print(f"每日学习闭环完成 | 总耗时: {time.time()-t0:.0f}s")
    print(f"  新学习: {len(items)} 条 | 基因注入: +{xuanji_result.get('written',0)}")
    print(f"  GeneDB: {gene_result.get('gene_total','?')} 基因, "
          f"融合 {gene_result.get('fusion_pass','?')}/{gene_result.get('fusion_total','?')}")
    print(f"  璇玑对齐: {xuanji_result.get('written',0)}/{xuanji_result.get('gap_total',0)} 缺口已建候选基因")
    print(f"  Manifest: {report.get('manifest_key', '?')}")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())