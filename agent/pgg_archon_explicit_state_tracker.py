"""
PGG Archon Explicit State Tracker
显式状态跟踪器：键值对状态管理 + checkpoint/history 回溯

用户可以从这篇文章学习：
https://hermes-agent.nousresearch.com/docs/... (链接待补充)

线程安全（threading.Lock），纯内存操作，不写 DB/文件。
"""

import copy
import threading
import time
import uuid
from typing import Any, Dict, List, Optional


class ExplicitStateTracker:
    """显式状态跟踪器，支持键值对状态管理 + checkpoint/history 回溯。

    核心行为：
    - 线程安全（threading.Lock）
    - 每次 set() 自动记录到 history（带时间戳和操作类型）
    - checkpoint 保存当前状态的深拷贝
    - rollback 恢复检查点状态并记录 rollback 事件到 history
    - 初始化时自动创建第一个 checkpoint
    """

    def __init__(self, namespace: str = "default"):
        self._namespace = namespace
        self._lock = threading.Lock()
        # 当前状态
        self._state: Dict[str, Any] = {}
        # 变更历史
        self._history: List[Dict[str, Any]] = []
        # 检查点字典 {checkpoint_id: state_snapshot}
        self._checkpoints: Dict[str, Dict[str, Any]] = {}
        # 自动创建初始 checkpoint
        self._create_initial_checkpoint()

    def _now(self) -> str:
        """返回当前时间戳字符串。"""
        return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())

    def _generate_id(self) -> str:
        """生成唯一标识符。"""
        return uuid.uuid4().hex[:12]

    def _create_initial_checkpoint(self):
        """初始化时自动创建第一个 checkpoint。"""
        cid = self._generate_id()
        self._checkpoints[cid] = copy.deepcopy(self._state)
        self._history.append({
            "type": "checkpoint",
            "checkpoint_id": cid,
            "timestamp": self._now(),
            "namespace": self._namespace,
        })

    # ---- 公开 API ----

    @property
    def namespace(self) -> str:
        """返回当前命名空间。"""
        return self._namespace

    def get(self, key: str, default: Any = None) -> Any:
        """获取指定 key 的状态值。

        Args:
            key: 状态键
            default: 键不存在时的默认值

        Returns:
            状态值，或 default
        """
        with self._lock:
            return self._state.get(key, default)

    def set(self, key: str, value: Any) -> Dict[str, Any]:
        """设置状态值，自动记录到 history。

        Args:
            key: 状态键
            value: 状态值

        Returns:
            包含操作结果的 dict：
            {'key': key, 'value': value, 'timestamp': ..., 'checkpoint_id': ...}
        """
        with self._lock:
            old_value = self._state.get(key, None)
            self._state[key] = value
            record = {
                "type": "set",
                "key": key,
                "value": copy.deepcopy(value),
                "old_value": copy.deepcopy(old_value),
                "timestamp": self._now(),
                "namespace": self._namespace,
            }
            self._history.append(record)
            return {
                "key": key,
                "value": value,
                "timestamp": record["timestamp"],
                "checkpoint_id": None,
            }

    def delete(self, key: str) -> bool:
        """删除指定 key 的状态。

        Args:
            key: 要删除的键

        Returns:
            如果 key 存在并删除成功返回 True，否则 False
        """
        with self._lock:
            if key not in self._state:
                return False
            old_value = self._state.pop(key)
            self._history.append({
                "type": "delete",
                "key": key,
                "old_value": copy.deepcopy(old_value),
                "timestamp": self._now(),
                "namespace": self._namespace,
            })
            return True

    def checkpoint(self) -> str:
        """创建检查点，保存当前状态的深拷贝。

        Returns:
            新创建的 checkpoint_id
        """
        with self._lock:
            cid = self._generate_id()
            self._checkpoints[cid] = copy.deepcopy(self._state)
            self._history.append({
                "type": "checkpoint",
                "checkpoint_id": cid,
                "timestamp": self._now(),
                "namespace": self._namespace,
            })
            return cid

    def rollback(self, checkpoint_id: str) -> bool:
        """回滚到指定检查点，恢复该点的所有状态值。

        回滚操作本身也会记录到 history。

        Args:
            checkpoint_id: 目标检查点 ID

        Returns:
            如果检查点存在并回滚成功返回 True，否则 False
        """
        with self._lock:
            if checkpoint_id not in self._checkpoints:
                return False
            snapshot = self._checkpoints[checkpoint_id]
            old_state = copy.deepcopy(self._state)
            self._state = copy.deepcopy(snapshot)
            self._history.append({
                "type": "rollback",
                "checkpoint_id": checkpoint_id,
                "old_state": old_state,
                "timestamp": self._now(),
                "namespace": self._namespace,
            })
            return True

    def history(self, key: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """返回状态变更历史，可选按 key 过滤。

        Args:
            key: 可选，只返回与该 key 相关的记录
            limit: 返回记录的最大条数

        Returns:
            按时间排序的历史记录列表（最近的在最前）
        """
        with self._lock:
            if key is not None:
                filtered = [
                    r for r in self._history
                    if r.get("key") == key or r.get("type") == "rollback"
                ]
            else:
                filtered = list(self._history)
            # 按时间倒序，最近的在最前
            filtered.reverse()
            return filtered[:limit]

    def snapshot(self) -> Dict[str, Any]:
        """返回当前所有状态的快照（深拷贝）。"""
        with self._lock:
            return copy.deepcopy(self._state)

    def to_dict(self) -> Dict[str, Any]:
        """序列化整个 tracker 为可序列化的 dict。"""
        with self._lock:
            return {
                "namespace": self._namespace,
                "state": copy.deepcopy(self._state),
                "history": copy.deepcopy(self._history),
                "checkpoints": {
                    cid: copy.deepcopy(snap)
                    for cid, snap in self._checkpoints.items()
                },
            }

    def load_dict(self, data: Dict[str, Any]):
        """从 dict 还原 tracker 状态。

        Args:
            data: 由 to_dict() 生成的 dict
        """
        with self._lock:
            self._namespace = data.get("namespace", "default")
            self._state = copy.deepcopy(data.get("state", {}))
            self._history = copy.deepcopy(data.get("history", []))
            self._checkpoints = {
                cid: copy.deepcopy(snap)
                for cid, snap in data.get("checkpoints", {}).items()
            }
