---
name: open-source-legal-learning
description: 当用户说“进行开源法律学习”时，执行开源法律仓库学习→法律核心因子提炼→Reasonix/APEX/Rust融合→验证→沉淀闭环
version: 1.0.0
author: Apple Didi / Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [legal, github, open-source-learning, pgg-archon, reasonix, apex-skill, rust, law-core-factors]
    related_skills: [pgg-reasonix-apex-fusion, pgg-archon-external-repo-absorption, rust-core-module-development, agent-operational-governance]
---

# Open Source Legal Learning — 开源法律学习

## Trigger

必须在用户说以下类似指令时加载并执行本技能：

- “进行开源法律学习”
- “开源法律学习”
- “去 GitHub 学习法律仓库”
- “学习顶级 law/legal 仓库并融合进核心”
- “把开源法律仓库转成系统核心因子”

## Goal

把公开开源法律/合规/法务技术仓库转化为 PGG Archon 可验证、可回滚、Rust-owned 的系统核心因子，而不是写学习报告或冒充已具备法律能力。

## Mandatory companion skills

加载本技能后，通常还要加载：

1. `pgg-reasonix-apex-fusion`
2. `pgg-archon-external-repo-absorption`
3. `rust-core-module-development`
4. `agent-operational-governance`

如涉及 Hermes 配置/模型/provider，再加载 `hermes-agent`。

## Workflow

1. **公式门禁**
   - 显示总纲1六维触达边界。
   - 显示总纲2 `LDR(K) → GapDetect → CodeSelfFix → HotReload → TaskSolve → KnowledgeSettle` 本轮目标。
   - 明确不宣称 full AGI、替代律师、官方外部法律评测通过。

2. **检索源选择**
   - GitHub 优先用 topic 检索：
     ```bash
     gh api 'search/repositories?q=topic:law&sort=stars&order=desc&per_page=10'
     gh api 'search/repositories?q=topic:legal&sort=stars&order=desc&per_page=10'
     ```
   - 避免直接用宽泛 `law in:name,description,readme` 作为 Top law 依据；该查询容易被 unrelated 高星项目污染。
   - 如用户指定 “前三”，记录排序口径：topic、stars、时间、语言、地域。

3. **证据采集**
   - 对每个候选仓库读取 metadata、license、topics、stars、default_branch、pushed_at。
   - README 使用：
     ```bash
     gh api repos/<owner>/<repo>/readme --jq .content | base64 --decode
     ```
   - 写入证据目录，保存 README 快照、repo cards、sha256。
   - 不整包复制高风险代码；许可证未知/AGPL 默认 REVIEW/BLOCK。

4. **多模型审计**
   - 进化/PGG/架构任务优先真实调用 GPT/Claude Responses API / `codex_responses`。
   - 记录 provider/model/api_mode/http_status/output_path/sha256。
   - 单模型失败必须如实标 `ERROR`，不得角色扮演冒充。
   - `execute_code` 可能不继承 provider secrets；必要时用 `terminal` Python 调用真实环境。

5. **因子提炼**
   - 输出因子必须包含：
     - `id`
     - `factor`
     - `source_repo`
     - `evidence`
     - `promote_rule`
     - `safety_boundary`
     - `formula_weight`
   - 法律因子只作为流程/检索/合规/风控门禁，不直接生成终局法律结论。
   - 示例因子：
     - `LAW-RAG-SOURCE-CONTEXT`：jurisdiction/source_hash/version/citation/doc_chunk 溯源门禁。
     - `LAW-RISK-CASE-TAXONOMY`：category/risk_signal/statute_hint/evidence_gap 风险矩阵。
     - `LAW-LICENSE-OBLIGATION-MATRIX`：obligations/permissions/limitations 许可证兼容矩阵。

6. **Rust 融合**
   - 优先写入已有 Rust fusion crate，例如：
     `/Users/appleoppa/.hermes/workspace/进化/rust/pgg_reasonix_apex`
   - 添加 Rust struct / manifest 字段 / tests。
   - 不修改 Hermes scheduler/security boundary，除非用户另行明确授权。

7. **验证**
   - 必须运行：
     ```bash
     cargo fmt
     cargo test
     cargo build --release
     ```
   - 生成 fusion manifest，读回字段与 sha256。
   - 测试至少覆盖：因子数量、权重合计、来源 repo、LLM 证据、anti-overclaim boundary。

8. **统一总账与沉淀**
   - 更新并读回：`/Users/appleoppa/.hermes/data/EVOLUTION_MANIFEST.json`
   - 生成报告到 `~/.hermes/workspace/` 对应证据/治理目录。
   - 如发现新坑，补写到本技能或 `pgg-reasonix-apex-fusion` reference。

## Output Contract

完成时必须给出：

- GitHub 检索口径与 Top 仓库列表。
- repo cards / README 快照 / sha256 路径。
- GPT/Claude 或其他 LLM 真实调用状态。
- Rust 修改位置。
- `cargo test` / `cargo build --release` 真实结果。
- fusion manifest 路径和 sha256。
- EVOLUTION_MANIFEST 读回摘要。
- 真实性边界与剩余 BLOCKED/WATCH。

## Pitfalls

- 宽泛 `law` 搜索会污染 Top 仓库排名。
- GitHub stars 是热度信号，不是法律权威。
- README/file existence 不等于能力融合；必须 Rust 编译和 manifest 读回。
- Claude/GPT 失败时不能冒充参与。
- 不要把“法律 AI 助手”项目直接等同为可办案能力。
- 不要把未知许可证/AGPL 仓库整包吸收进核心。
- safety boundary 建议写“必须由专业人工复核”，避免暗示系统替代律师。

## Core landing addendum

当用户要求“落地”“固化”“融合进核心”时，不得停在技能创建；必须把触发模式写入 Rust-generated manifest / EVOLUTION_MANIFEST 并运行 cargo 验证。详细步骤见 `references/core-mode-landing-pattern-20260606.md`。

## Reference

本技能首轮成功样例与证据：

- `/Users/appleoppa/.hermes/workspace/进化/证据/Reasonix-APEX-SKILL-20260602/law-core-factors-20260606/LAW_CORE_FACTORS_FUSION_REPORT.md`
- `/Users/appleoppa/.hermes/skills/workflow/pgg-reasonix-apex-fusion/references/law-core-factors-github-topic-law-fusion-20260606.md`

本技能后续刷新/复跑模式：

- `references/dynamic-llm-audit-evidence-and-gh-api-pattern-20260606.md` — 当前轮 open-source legal learning 的动态 LLM 审计证据注入、GitHub API GET 查询、provider key 环境差异、Rust manifest 生成与验证模式。
