PGG Archon/苹果中枢执行纪律：低风险可逆且评分>75%时连续推进到测试、读回、交付；禁止停在建议、计划或漂亮报告。
§
真实性治理：文件存在≠能力完成，URL可达≠能力可用，服务启动≠链路参与；完成声明必须有代码/命令/日志/状态/账本读回证据。
§
核心状态索引：PGG Archon 统一总账在 `/Users/appleoppa/.hermes/data/EVOLUTION_MANIFEST.json`；背景进化证据在 `~/.hermes/data/pgg-background-evolution/`；新对话先读 SOUL/USER/MEMORY/manifest/相关 skill。
§
当前系统名与边界：PGG Archon 是有效系统名；APEX RuntimeOS 为历史实现层；法律 AGI Phase217 是有边界办案流程门禁强化版，禁止称 full AGI、零风险、替代律师或官方外评通过。
§
模型底线：GPT/Claude 禁走 `/v1/chat/completions`；`gpt55_5yuantoken` 与 `claude_opus46_5yuantoken` 固定 `api_mode: codex_responses` / Responses API；DeepSeek/MiMo/MiniMax 等按各自 verified API mode。
§
ChuangAgent 固化规则：`gpt55_5yuantoken`=`https://chuangagent.eu.cc/v1` + `gpt-5.5` + `GPT55_5YUANTOKEN_API_KEY`；`claude_opus46_5yuantoken`=`https://chuangagent.eu.cc/v1` + `claude-opus-4-6` + `CLAUDE_OPUS47_5YUANTOKEN_API_KEY`；Web UI `/api/hermes/available-models` 必须传递 custom provider 的 `api_mode/key_env`，不得显示或退回 chat_completions。
§
Hermes/Web UI 配置排障优先读取 skill `hermes-agent` 与 `hermes-config-runtime-diagnosis`；GPT/Claude Responses + Web UI api_mode/key_env 经验见 `hermes-config-runtime-diagnosis/references/chuangagent-responses-webui-provider-scope-20260605.md`。
§
办案纪律：启动办案必须先核实代理方、案件类型、当事人、材料路径、目标交付物、时限；先运行 `~/.hermes/bin/cms_case_guard --next` 取全局编号，归档后运行 `cms_case_guard --validate <case_root> --case-type <案件类型>`，审计未过不得称终版/办结。
§
案件编号与文件规则：案件编号 4 位序号全局累加，开案前扫描 `~/.hermes/workspace/苹果中枢办案库/` 与 `外部案件档案_legacy_home/` 取最高+1；刑事代码 XS，民商事代码 MS；案件文件名前缀必须完整案件编号。
§
文件治理：Home 根目录保持极简；PGG/Hermes 产物归入 `~/.hermes/workspace/` 对应分区；办案库只放案件档案/台账，PGG 治理/工具产物放 `~/.hermes/workspace/pgg-archon-governance/`，桌面输出需用户明确授权。
§
Rust 路线稳定事实：核心/性能模块优先 Rust；cargo 稳定路径 `/Users/appleoppa/.cargo/bin/cargo`；macOS PyO3 编译后需 codesign；缺 PATH 时用绝对路径。
§
Hermes background 运行纪律：后台 Python 导入 Hermes agent 模块时显式 `PYTHONPATH=$HOME/.hermes/hermes-agent`；长跑任务用 `terminal(background=true, notify_on_complete=true)`，避免反复空 poll。
§
记忆分层治理：MEMORY/USER 只存长期红线、稳定偏好和索引；历史过程入 session_search/archive，流程入 skill/reference，状态入 manifest，长知识入 retrieval/APEX-MEM/akashic；memory 满时先备份、分层归档、瘦身，不盲目加上限。
§
GPT55 benchmark边界纠正：当前会话主通道和 Hermes CLI `custom:gpt55_5yuantoken` 可用时，raw urllib `/v1/responses` 的 502/output=[] 只能说明 direct adapter/payload/并发代理不等价，不能判定 GPT 不可用；GPT benchmark 应复用 Hermes CLI 或正式 provider adapter。
§
开源法律学习触发：用户说“进行开源法律学习/开源法律学习”时，加载 skill `open-source-legal-learning`，按 GitHub law/legal 仓库检索→证据采集→真实 LLM 审计→Rust 因子融合→cargo 验证→EVOLUTION_MANIFEST 读回闭环执行。
§
开源法律学习自主进化已落地为 `open-source-legal-learning` skill + Rust crate `/Users/appleoppa/.hermes/workspace/进化/rust/pgg_reasonix_apex` autonomy controller + cron 双频：每日 LIGHT_SCAN job `45bab2922501`，每两天 DEEP_FUSION job `1fbc29a5ed64`；总账索引 `EVOLUTION_MANIFEST.json.open_source_legal_learning_autonomy_runtime`。
§
Hermes Web UI stable runtime baseline: Node must stay on upgraded `/usr/local/bin/node` v24.14.1; Web UI package canonical root is `/Users/appleoppa/.hermes/webui/node_modules/hermes-web-ui`; old npm/nvm/global paths should be symlinks to this root. Verify with health `node_version=24.14.1`, `webui_version=0.6.11`, `webui_update_available=false`. Do not fix Web UI by reverting to NVM Node v23/v22.
§
OmniRoute GPT55 lane reconciliation (2026-06-06): GPT55 main/orchestrator lane (`custom:gpt55_5yuantoken`, gpt-5.5) is usable and has been driving the session. The prior 502 issue was specifically the router/provider proof lane in `agent/pgg_archon_external_benchmark_provider_run.py`, caused by Responses payload shape; fixed by using plain `input` string + `max_completion_tokens` with `max_tokens` retry. Do not say 'GPT55 unavailable' globally; say proof lane issue if relevant.
§
PilotDeck 本地私有同步仓库已创建为 `https://github.com/appleoppa/PilotDeck-apple-sync`（PRIVATE）。本地 OpenBMB 源仓库是 shallow，直接推送会因缺对象失败；已用 clean snapshot 私有镜像推送，`.env/auth.db/node_modules` 排除。OpenBMB LFS 预算阻断导致 51 个媒体/图标文件可能仍为 LFS pointer；私有镜像已中和 `.gitattributes` LFS filter 并在 `docs/apple-sync/DEPLOY_FROM_PRIVATE_REPO.md` 记录边界。
