# 超级进化10.1 运行与修复备忘

## 1. 真正验证过的结果

- `hermes_full_toolcall_planner.py` 能把输入材料转成全局轨迹 JSON。
- `hermes_full_toolcall_runtime.py` 能跑出并行调度闭环。
- 初版运行时所有任务落到 `local_fallback`，说明负载均衡策略有缺口。
- 修正 `choose_worker` 后，再跑一次，任务分配到了 `minimax_m27_highspeed`。
- `hermes_skill_promotion_gate.py` 能读取候选轨迹并按证据门禁 patch 正式 skill。

## 2. 关键修复点

- 不要让 `local_fallback` 参与主候选排序；它应只在真实 worker 不可用时使用。
- 技能晋升要看候选证据是否齐全，不要把“有候选文件”直接当作“正式技能已更新”。
- shell 命令里带 Python 代码或脚本名时，避免反引号触发命令替换。

## 3. 读回验证清单

- 运行 JSON 是否存在。
- `workers_used` 是否显示真实 worker。
- 晋升报告 JSON 是否写出。
- 正式 `SKILL.md` 是否真的包含新增模块。

## 4. 适用范围

- 只适用于 sidecar 并行调度和技能候选晋升。
- 不用于核心源码改造。
