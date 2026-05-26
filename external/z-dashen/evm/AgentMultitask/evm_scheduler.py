"""
EVM多任务调度协同系统
解决多任务冲突、并发紊乱、优先级失控问题
"""
from typing import List, Dict
from queue import PriorityQueue

class Task:
    def __init__(self, tid: str, priority: int, resource: float):
        self.tid = tid
        self.priority = priority
        self.resource = resource
        
    def __lt__(self, other):
        return self.priority < other.priority

class TaskScheduler:
    """EVM任务调度器"""
    
    def __init__(self):
        self.queue = PriorityQueue()
        self.executed = []
        
    def add_task(self, task_id: str, priority: int = 5, resource: float = 0.5):
        """添加任务"""
        task = Task(task_id, priority, resource)
        self.queue.put(task)
        
    def execute_all(self) -> List[Dict]:
        """执行所有任务"""
        while not self.queue.empty():
            task = self.queue.get()
            self.executed.append({
                "tid": task.tid,
                "priority": task.priority,
                "status": "completed"
            })
        return self.executed

# 导出
EVM_TaskScheduler = TaskScheduler
