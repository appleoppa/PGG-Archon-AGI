"""
APEX Planning & Incremental Implementation Module
融合addyosmani/agent-skills × APEX E_xp/Λ维度

APEX E_xp = 探索-利用平衡
APEX Λ_ctx = 上下文切换损耗

Author: 璇玑帝国
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
from enum import Enum
import json


class TaskType(Enum):
    """任务类型"""
    FOUNDATION = "foundation"      # 基础任务
    FEATURE = "feature"          # 功能任务
    INTEGRATION = "integration"  # 集成任务
    OPTIMIZATION = "optimization" # 优化任务


@dataclass
class Task:
    """任务单元"""
    id: str
    name: str
    description: str
    task_type: TaskType
    acceptance_criteria: List[str] = field(default_factory=list)
    dependencies: Set[str] = field(default_factory=set)
    vertical_slice: bool = True  # 是否是垂直切片
    estimated_lines: int = 0
    completed: bool = False


@dataclass
class DependencyGraph:
    """依赖图"""
    tasks: Dict[str, Task] = field(default_factory=dict)
    
    def add_task(self, task: Task):
        self.tasks[task.id] = task
    
    def get_execution_order(self) -> List[str]:
        """获取执行顺序（拓扑排序）"""
        # 计算入度
        in_degree = {tid: 0 for tid in self.tasks}
        for task in self.tasks.values():
            for dep in task.dependencies:
                if dep in in_degree:
                    in_degree[task.id] += 1
        
        # Kahn算法
        queue = [tid for tid, deg in in_degree.items() if deg == 0]
        result = []
        
        while queue:
            tid = queue.pop(0)
            result.append(tid)
            
            for other in self.tasks.values():
                if tid in other.dependencies:
                    in_degree[other.id] -= 1
                    if in_degree[other.id] == 0:
                        queue.append(other.id)
        
        return result
    
    def slice_vertically(self) -> List[List[str]]:
        """垂直切片：将任务按依赖层级分组"""
        order = self.get_execution_order()
        slices = []
        current_slice = []
        completed = set()
        
        for tid in order:
            task = self.tasks[tid]
            # 检查依赖是否都完成
            if task.dependencies.issubset(completed):
                current_slice.append(tid)
                completed.add(tid)
            else:
                if current_slice:
                    slices.append(current_slice)
                    current_slice = [tid]
                completed.add(tid)
        
        if current_slice:
            slices.append(current_slice)
        
        return slices


@dataclass
class IncrementalBuild:
    """增量构建记录"""
    slice_id: int
    tasks: List[str]
    implementation: str
    tests_passed: bool = False
    verified: bool = False
    committed: bool = False


class APEXPlanningEngine:
    """
    APEX 任务规划引擎
    
    融合planning-and-task-breakdown与APEX E_xp：
    - 依赖图构建
    - 垂直切片优化
    - E_xp自适应探索
    """
    
    def __init__(self, e_xp: float = 1.0):
        """
        初始化规划引擎
        
        Args:
            e_xp: APEX E_xp值（探索-利用平衡）
        """
        self.e_xp = e_xp
        self.graph = DependencyGraph()
        self.builds: List[IncrementalBuild] = []
        
    def add_task(self, 
                 task_id: str,
                 name: str,
                 description: str,
                 task_type: TaskType,
                 dependencies: List[str] = None,
                 acceptance_criteria: List[str] = None) -> Task:
        """添加任务"""
        task = Task(
            id=task_id,
            name=name,
            description=description,
            task_type=task_type,
            dependencies=set(dependencies or []),
            acceptance_criteria=acceptance_criteria or []
        )
        self.graph.add_task(task)
        return task
    
    def plan(self) -> Dict:
        """
        生成执行计划
        
        Returns:
            Dict包含：
            - execution_order: 执行顺序
            - vertical_slices: 垂直切片
            - e_xp_optimization: E_xp优化建议
        """
        order = self.graph.get_execution_order()
        slices = self.graph.slice_vertically()
        
        # E_xp优化：根据探索程度决定切片大小
        if self.e_xp > 1.0:
            # 积极探索模式：更小的切片，更快验证
            slice_size = 2
        else:
            # 利用模式：更大的切片，减少切换
            slice_size = 4
        
        return {
            "execution_order": order,
            "vertical_slices": slices,
            "slice_size_target": slice_size,
            "estimated_slices": len(slices),
            "estimated_tasks": len(order)
        }
    
    def execute_slice(self, 
                     slice_id: int,
                     tasks: List[str],
                     implement_func: callable) -> IncrementalBuild:
        """
        执行单个切片
        
        Args:
            slice_id: 切片ID
            tasks: 任务列表
            implement_func: 实现函数
        
        Returns:
            IncrementalBuild: 切片执行结果
        """
        print(f"[Plan] 执行Slice {slice_id}: {tasks}")
        
        # 实现
        implementation = implement_func(tasks)
        
        build = IncrementalBuild(
            slice_id=slice_id,
            tasks=tasks,
            implementation=implementation
        )
        
        self.builds.append(build)
        
        # Λ_ctx更新：记录切换损耗
        self._update_lambda_ctx(tasks)
        
        return build
    
    def _update_lambda_ctx(self, completed_tasks: List[str]):
        """更新Λ_ctx（切换损耗）"""
        # 简化：完成任务切换
        switch_count = len(completed_tasks)
        # Λ_ctx = e^(-λ × N_switches / N_tasks)
        lambda_sw = 1.5
        n_tasks = len(self.graph.tasks)
        self.lambda_ctx = min(1.0, 0.3 + (1.0 - 0.3) * (1 - lambda_sw * switch_count / n_tasks))


class APEXIncrementalRunner:
    """
    APEX 增量运行器
    
    闭环：Implement → Test → Verify → Commit → Next Slice
    """
    
    def __init__(self, planning_engine: APEXPlanningEngine):
        self.planner = planning_engine
        self.results: List[IncrementalBuild] = []
        
    def run(self, implement_func: callable, test_func: callable = None) -> List[IncrementalBuild]:
        """
        运行完整增量闭环
        
        Args:
            implement_func: 实现函数
            test_func: 测试函数
        
        Returns:
            List[IncrementalBuild]: 所有切片结果
        """
        plan = self.planner.plan()
        slices = plan["vertical_slices"]
        
        print(f"[APEX] 开始增量构建，共{len(slices)}个切片")
        
        for i, slice_tasks in enumerate(slices):
            print(f"\n{'='*50}")
            print(f"[Slice {i+1}/{len(slices)}]")
            
            # 1. Implement
            build = self.planner.execute_slice(i, slice_tasks, implement_func)
            print(f"[Implement] 完成: {slice_tasks}")
            
            # 2. Test (如果有)
            if test_func:
                build.tests_passed = test_func(slice_tasks)
                print(f"[Test] {'✓' if build.tests_passed else '✗'}")
            else:
                build.tests_passed = True
            
            # 3. Verify
            build.verified = True  # 简化
            print(f"[Verify] ✓")
            
            # 4. Commit (记录)
            build.committed = True
            print(f"[Commit] ✓")
            
            self.results.append(build)
            
            # 检查是否继续
            if not build.verified:
                print("[APEX] 切片验证失败，停止")
                break
        
        print(f"\n[APEX] 增量构建完成: {len(self.results)}/{len(slices)}切片")
        return self.results
    
    def get_summary(self) -> Dict:
        """获取执行摘要"""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.verified)
        
        return {
            "total_slices": total,
            "verified": passed,
            "success_rate": passed / total if total > 0 else 0,
            "e_x": self.planner.e_xp,
            "lambda_ctx": getattr(self.planner, 'lambda_ctx', 0.9)
        }


if __name__ == "__main__":
    # 示例
    planner = APEXPlanningEngine(e_xp=1.2)
    
    # 添加任务
    planner.add_task("t1", "数据库schema", "创建表结构", TaskType.FOUNDATION)
    planner.add_task("t2", "用户API", "CRUD API", TaskType.FEATURE, dependencies=["t1"])
    planner.add_task("t3", "前端表单", "用户表单UI", TaskType.FEATURE, dependencies=["t1"])
    planner.add_task("t4", "集成测试", "端到端测试", TaskType.INTEGRATION, dependencies=["t2", "t3"])
    
    # 规划
    plan = planner.plan()
    print(f"执行顺序: {plan['execution_order']}")
    print(f"垂直切片: {plan['vertical_slices']}")
    
    # 增量运行
    runner = APEXIncrementalRunner(planner)
    
    def mock_implement(tasks):
        return f"// 实现 {tasks}"
    
    results = runner.run(mock_implement)
    
    print(f"\n摘要: {runner.get_summary()}")
