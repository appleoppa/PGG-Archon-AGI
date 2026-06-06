# 法律 Agent + MIMO 第三方审计验证工作流

适用：用户要求用真实法律数据、案件流程、第三方 LLM 审计来验证法律 AI / AGI 能力时。

## 核心原则

- MIMO 只作为第三方审计 LLM，不作为主办案模型。
- 法律结论必须区分：内部草稿、可审查草稿、对外交付版。
- 未核验法条原文、案例原文和现行有效状态前，不得输出确定条号/裁判规则作为最终依据。
- "权威源种子已验证"不能说成"国内/全球最强全量法律法规案件数据库已完成"。

## MIMO provider 约定

```text
provider name: mimo_v25_pro_auditor
model: mimo-v2.5-pro
base_url: https://token-plan-cn.xiaomimimo.com/v1
key_env: MIMO_V25_PRO_API_KEY
api_mode: chat_completions
role: third-party audit only
```

验证时先检查：

1. `/models` 是否返回 `mimo-v2.5-pro`。
2. `/chat/completions` 是否返回有效 `response_id`。
3. 不打印 key；只记录 key env name、status、response_id、hash。

## 法律权威源 seed registry

推荐至少验证这些入口的可达性和来源属性：

- 国家法律法规数据库：`https://flk.npc.gov.cn/`
- 最高人民法院：`https://www.court.gov.cn/`
- 最高人民检察院：`https://www.spp.gov.cn/`
- 中国裁判文书网：`https://wenshu.court.gov.cn/`
- 中国政府网：`https://www.gov.cn/`
- United Nations Treaty Collection：`https://treaties.un.org/`
- WTO Documents：`https://docs.wto.org/`
- WIPO Lex：`https://www.wipo.int/wipolex/`
- Legal Information Institute：`https://www.law.cornell.edu/`
- EUR-Lex：`https://eur-lex.europa.eu/`

只做 HEAD/GET 可达性验证时，只能称为"权威来源种子验证"，不能称为已经建成全量数据库。

## 全流程 Agent 验证链

最小闭环：

1. `case_intake_agent`：事实、主体、案由、请求、管辖。
2. `evidence_management_agent`：证据清单、证明目的、缺口。
3. `legal_research_agent`：检索权威源入口与待核验法条/案例。
4. `case_strategy_agent`：请求权衡、风险、举证策略。
5. `document_drafting_agent`：只生成带核验标记的草稿。
6. `inspection_audit_agent`：查法条、案例、事实和引用是否可交付。
7. `third_party_llm_auditor`：MIMO 审计是否夸大、是否可交付、风险与下一步。

## 评分维度

维度示例：

- source_registry
- agent_flow
- anti_hallucination_gate
- case_process_coverage
- global_source_coverage_seed
- official_text_extraction
- official_case_dataset_depth
- third_party_audit_channel
- professional_reliability

如果 `official_text_extraction` 或 `official_case_dataset_depth` 低，不得对外宣称数据库完整。

## official_text_extraction 实测方法（Phase 211 硬教训）

**必须用真实文件实测，不能用 URL 可达性替代：**

1. **工具准备**：
   - `pdftotext`（poppler-utils）
   - `tesseract` v5.5.2，chi_sim+eng 语言包
   - `pdftoppm`（PDF → 图像转换）
   - `pdfimages`（图像提取）

2. **测试集**：至少 5 个真实法律 PDF，**必须同时包含**：
   - 文本型 PDF（可嵌入文本）
   - 扫描型 PDF（图像嵌入）

3. **执行命令**：
   ```bash
   # 文本型 PDF
   pdftotext /path/to/文件.pdf /tmp/output.txt
   # 扫描型 PDF：先转图像，再 OCR
   pdftoppm -png -r 400 /path/to/文件.pdf /tmp/page
   tesseract /tmp/page-1.png stdout -l chi_sim+eng > /tmp/ocr_output.txt
   ```

4. **判定标准**：
   - 文本型 PDF：提取率 ≥80% 且中文字符数 >0 → PASS
   - 扫描型 PDF：中文字符数 >0 → PASS；返回 0 字符 → FAIL
   - **"工具有了" ≠ "工具能用"**：tesseract installed ≠ OCR working

5. **评分纪律**：
   - 不得仅因"工具有了"就加分；必须有**可重复执行的实测证据**
   - 拟升分被实测打脸时，**必须维持原分**，不得美化
   - OCR 返回 0 字符时不得声称"OCR 管道可用"
   - 如需对外报告分项分数，每项必须有对应实测记录

**Phase 211→212 纠错完整过程**：

- Phase 211 对扫描型 PDF 误用 pdftotext（应为 pdftoppm + tesseract）
- execute_code sandbox 的 /tmp 与 host /tmp 隔离，OCR 输出的图片在 sandbox 内不可见
- 导致 tesseract 报错 "failed to open locally"，误判为"管道完全失败"
- Phase 212 在 host terminal 直接执行：pdftoppm -r 400 -png + tesseract chi_sim+eng --psm 6 → 75% 扫描型成功

**正确 OCR 流程（实测有效）**：
```bash
# 扫描型 PDF（必须用此流程）
pdftoppm -r 400 -png -l 1 /path/to/file.pdf /tmp/page_prefix
tesseract /tmp/page_prefix-1.png stdout -l chi_sim+eng --psm 6 > /tmp/output.txt

# 文本型 PDF（首选 pdftotext）
pdftotext -layout /path/to/file.pdf /tmp/output.txt
```

**关键参数**：`-r 400`（300 DPI 以下文字模糊导致 tesseract 识别失败）、`--psm 6`（统一文本块模式）、`-l chi_sim+eng`（简体中文+英文语言包）。

**execute_code /tmp 隔离的解决方案**：所有涉及文件 IO 的 OCR/PDF 测试，必须用 `terminal()` 而非 `execute_code()`。execute_code 的 sandbox 环境与 host 完全隔离，/tmp 文件不互通。

### MIMO 阻断时的 MiniMax CN 降级审计（Phase 211→212 实测补充）

当 MIMO (`mimo_v25_pro_auditor`) 被 macOS proxy 阻断（exit 35）时，可按用户指令降级使用 MiniMax CN 执行审计：

**1. 确认 MiniMax CN 通道可用**

MiniMax CN 的 `.env` key 名称是 `MINIMAX_CN_API_KEY`（注意：不是 `MINIMAX_API_KEY`），base_url 是 `https://api.minimaxi.com/v1`，模型是 `MiniMax-M2.7-Highspeed`。

**2. 读取 .env 的正确方式**

```python
import os
env_path = os.path.expanduser('~/.hermes/.env')
env_vars = {}
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            env_vars[k] = v

api_key = env_vars.get('MINIMAX_CN_API_KEY', '')
```

> 注意：venv 激活（`source .venv/bin/activate`）在某些环境下失败，需直接读 `.env` 文件获取 key。

**3. MiniMax CN 审计调用示例**

```python
import httpx
payload = {
    "model": "MiniMax-M2.7-Highspeed",
    "messages": [{"role": "user", "content": "审计内容"}],
    "max_tokens": 300
}
headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
with httpx.Client(timeout=30) as client:
    r = client.post("https://api.minimaxi.com/v1/chat/completions", json=payload, headers=headers)
    result = r.json()
    print(result['choices'][0]['message']['content'])
```

**4. 审计结果写入 GeneDB 和报告**

审计结果更新到 JSON 报告的 `mimo_audit` 字段，记录 `provider: "minimax_cn"`, `model`, `channel_status: "AVAILABLE"`，并在 `audit_trail` 中注明 "MiniMax CN 通道降级替代，按用户指令执行"。

**Phase 211 实测**：MiniMax CN 审计 PASS——诚实性审计通过，Phase 211 报告主动自我更正（62分→55分）体现诚实纠正机制。

## 输出纪律

报告必须写清：

- 已完成：provider 接入、来源 seed 验证、流程 Agent、反幻觉门禁、审计 response_id、**实测结果**。
- 未完成：全量法条抽取、官方案例库深度、真实案件 benchmark。
- 可交付等级：内部验证 / 有限试点 / 对外交付。
- **实测证据**：每个提升分必须有可重复执行的测试证据，不得用推测代替测试。
