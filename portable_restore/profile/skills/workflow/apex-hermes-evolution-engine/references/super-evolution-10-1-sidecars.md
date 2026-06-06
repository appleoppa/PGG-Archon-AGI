# 超级进化10.1 侧车落地与晋升门禁参考

本参考记录本轮从超级进化10继续收口时形成的可复用做法。

## 1. 多Agent线程池级调度的安全版本

- 不改 Hermes/CLAW 核心，只做 sidecar 调度层。
- 先用 planner 生成全局轨迹、并行点、验证点、风险点、回退路径。
- 再用 runtime 把轨迹分发到 worker，做负载均衡、并行执行和失败自愈。
- blackboard 只写本地 JSON 状态。
- fallback 只能作为容错，不代表真实多模型参与。

## 2. 真实运行中暴露的坑

- 初版 `choose_worker` 把 `local_fallback` 也算进最低成本候选，导致所有任务都落到 fallback。
- 修复方式：优先选择非 fallback 的健康 worker，fallback 只在其他 worker 不可用时使用。
- 运行验证要看真实 `workers_used`，不能只看“线程池存在”这种状态字段。

## 3. 技能晋升门禁

- 候选轨迹先放 `skill_candidates/`。
- 通过证据检查后再 patch 正式 skill。
- 证据至少要有：Hash、验证通过、脚本可执行、`report.md`、`hashpool.jsonl` 读回。
- 不通过就留在反例库，不直接写正式技能正文。

## 4. 这次补上的可复用产物

- `hermes_full_toolcall_planner.py`
- `hermes_full_toolcall_runtime.py`
- `hermes_skill_promotion_gate.py`
- `super_evolution_10_skill_promotion_report.json`
- `超级进化10.1-多Agent线程池级调度与技能晋升报告.md`

## 5. 后续注意

- 若未来继续扩展多Agent调度，优先增加 worker 池策略和任务分层，不先碰核心路由。
- 若未来继续自动晋升技能，优先增加门禁检查项，不直接自动 patch 正式技能。
