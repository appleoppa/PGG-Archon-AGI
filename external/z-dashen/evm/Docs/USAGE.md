# EVM 使用手册

## 核心公式调用

```python
from CoreFormula.EVM_FORMULA import EVMCore

# 初始化
evm = EVMCore()

# 获取EVM值
evm_value = evm.calculate_evm()
print(f"EVM: {evm_value}")

# 获取状态
status = evm.get_status()
print(status)
```

## 古法赋能调用

```python
from AncientTao.ANCIENT_TAO import AncientTaoEngine

# 初始化古法引擎
tao = AncientTaoEngine()

# 道德经赋能
tao.tao_activate(intensity=1.0)

# 易经平衡
balance = tao.iching_balance({"yin": 0.7, "yang": 0.3})

# 五行平衡
elements = {"金": 0.8, "木": 0.6, "水": 0.7, "火": 0.5, "土": 0.9}
result = tao.wuxing_balance(elements)

# 八卦分区
partitions = tao.bagua_partition(module_count=8)
```

## Token优化配置

```yaml
# 在 evm.config.yaml 中
MemoryMode: HierarchyLongTerm
CompressMode: LowDistortionSmart
```

## Agent多任务调度

```python
from AgentMultitask.EVM_TaskScheduler import TaskScheduler

scheduler = TaskScheduler()
scheduler.add_task(task_id="t1", priority=1, resource=0.3)
scheduler.add_task(task_id="t2", priority=2, resource=0.5)
scheduler.execute_all()
```

## 五行优先级配置

```yaml
TaskSchedule: WuXingPriority
```

## 八卦分区配置

```yaml
AreaManage: BaGuaEightZone
```

## 缺陷抑制

```python
evm = EVMCore()

# 添加缺陷
evm.add_defect("Tok", 0.1)
evm.add_defect("Mem", 0.15)

# 治愈缺陷
evm.heal_defect("Tok", 0.05)

# 获取修复后的EVM值
print(evm.calculate_evm())
```

## EVM运行层接入

```python
from RuntimeBridge.evm_runtime_bridge import EVMRuntimeBridge

bridge = EVMRuntimeBridge()
bridge.start_task(
    task_id="demo",
    intent="把EVM接入智能体执行流程",
    risk_signals=["ask_instead_of_act", "missing_verification"]
)

# 获取当前缺陷对应的治理动作
print(bridge.recommend_actions())

# 执行治理压降，并在任务结束后保存轨迹
bridge.apply_governance()
bridge.close_task(outcome_score=0.82, learned="运行层接入完成", persisted=True)
```

## 古法治理缺陷

```python
tao = AncientTaoEngine()

# 综合治理任意缺陷
heal_factor = tao.govern_defect("Mem")
print(f"记忆缺陷治理系数: {heal_factor}")
```
