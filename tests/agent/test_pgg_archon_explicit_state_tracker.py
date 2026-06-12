"""
Tests for PGG Archon ExplicitStateTracker.
"""

import time
import pytest

from agent.pgg_archon_explicit_state_tracker import ExplicitStateTracker


class TestExplicitStateTracker:
    """Test suite for ExplicitStateTracker."""

    def test_init_creates_default_checkpoint(self):
        """初始化时自动创建第一个 checkpoint。"""
        tracker = ExplicitStateTracker("test_init")
        history = tracker.history(limit=100)
        # 第一条历史记录应该是 checkpoint
        assert len(history) >= 1
        assert history[-1]["type"] == "checkpoint"  # 第一条（最早）
        # to_dict 中应该有一个 checkpoint
        data = tracker.to_dict()
        assert len(data["checkpoints"]) == 1

    def test_set_and_get(self):
        """set 后 get 返回正确的值。"""
        tracker = ExplicitStateTracker("test_set_get")
        tracker.set("name", "Alice")
        assert tracker.get("name") == "Alice"

    def test_set_returns_metadata(self):
        """set 返回包含 key/value/timestamp 的 dict。"""
        tracker = ExplicitStateTracker("test_set_meta")
        result = tracker.set("color", "blue")
        assert result["key"] == "color"
        assert result["value"] == "blue"
        assert "timestamp" in result
        assert "checkpoint_id" in result

    def test_get_default(self):
        """不存在的 key 返回 default 值。"""
        tracker = ExplicitStateTracker("test_default")
        assert tracker.get("nonexistent") is None
        assert tracker.get("nonexistent", 42) == 42

    def test_delete_existing_key(self):
        """删除存在的 key 返回 True。"""
        tracker = ExplicitStateTracker("test_del_exist")
        tracker.set("temp", "value")
        assert tracker.delete("temp") is True
        assert tracker.get("temp") is None

    def test_delete_missing_key(self):
        """删除不存在的 key 返回 False。"""
        tracker = ExplicitStateTracker("test_del_missing")
        assert tracker.delete("ghost") is False

    def test_checkpoint_creates_id(self):
        """checkpoint 返回非空字符串 ID。"""
        tracker = ExplicitStateTracker("test_cp_id")
        cid = tracker.checkpoint()
        assert isinstance(cid, str)
        assert len(cid) > 0

    def test_rollback_restores_values(self):
        """rollback 恢复检查点时刻的所有状态值。"""
        tracker = ExplicitStateTracker("test_rollback")
        tracker.set("a", 1)
        tracker.set("b", 2)
        cp1 = tracker.checkpoint()
        tracker.set("a", 100)
        tracker.set("c", 3)
        assert tracker.get("a") == 100
        assert tracker.get("c") == 3

        # 回滚到 cp1
        ok = tracker.rollback(cp1)
        assert ok is True
        assert tracker.get("a") == 1
        assert tracker.get("b") == 2
        assert tracker.get("c") is None  # cp1 之后添加的 key 消失了

    def test_rollback_invalid_checkpoint(self):
        """不存在的 checkpoint_id 回滚返回 False。"""
        tracker = ExplicitStateTracker("test_rollback_invalid")
        assert tracker.rollback("nonexistent_cp") is False

    def test_history_records_operations(self):
        """history 记录了所有 set/delete/checkpoint/rollback 操作。"""
        tracker = ExplicitStateTracker("test_history")
        tracker.set("x", 10)
        tracker.set("y", 20)
        tracker.delete("y")
        hist = tracker.history()
        # 应该有: init checkpoint + set x + set y + delete y
        # history() 返回倒序
        types = [h["type"] for h in hist]
        assert types[0] == "delete"
        assert "set" in types
        assert "checkpoint" in types

    def test_history_filter_by_key(self):
        """history 支持按 key 过滤。"""
        tracker = ExplicitStateTracker("test_hist_filter")
        tracker.set("a", 1)
        tracker.set("b", 2)
        tracker.set("a", 3)
        hist_a = tracker.history(key="a")
        for h in hist_a:
            assert h.get("key") == "a" or h["type"] == "rollback"

    def test_history_limit(self):
        """history 的 limit 参数生效。"""
        tracker = ExplicitStateTracker("test_hist_limit")
        for i in range(10):
            tracker.set(f"k{i}", i)
        hist = tracker.history(limit=3)
        assert len(hist) == 3

    def test_snapshot(self):
        """snapshot 返回当前状态的深拷贝。"""
        tracker = ExplicitStateTracker("test_snapshot")
        tracker.set("x", {"nested": "value"})
        snap = tracker.snapshot()
        assert snap["x"]["nested"] == "value"
        # 修改 snapshot 不应影响 tracker
        snap["x"]["nested"] = "modified"
        assert tracker.get("x")["nested"] == "value"

    def test_multi_namespace_isolation(self):
        """不同 namespace 的状态完全隔离。"""
        t1 = ExplicitStateTracker("ns1")
        t2 = ExplicitStateTracker("ns2")
        t1.set("key", "value1")
        t2.set("key", "value2")
        assert t1.get("key") == "value1"
        assert t2.get("key") == "value2"
        assert t1.namespace == "ns1"
        assert t2.namespace == "ns2"

    def test_to_dict_and_load_dict_roundtrip(self):
        """to_dict / load_dict 往返后状态一致。"""
        tracker = ExplicitStateTracker("test_serialize")
        tracker.set("a", 1)
        tracker.set("b", [1, 2, 3])
        cp1 = tracker.checkpoint()
        tracker.set("a", 99)

        data = tracker.to_dict()
        # 创建一个新的 tracker 并加载
        tracker2 = ExplicitStateTracker("fresh")
        tracker2.load_dict(data)
        assert tracker2.get("a") == 99
        assert tracker2.get("b") == [1, 2, 3]
        assert tracker2.namespace == "test_serialize"
        # 应该能回滚到同一个 checkpoint
        ok = tracker2.rollback(cp1)
        assert ok is True
        assert tracker2.get("a") == 1

    def test_thread_safety(self):
        """并发 set 不会丢失数据（线程安全）。"""
        import threading

        tracker = ExplicitStateTracker("test_thread")
        n = 100
        errors = []

        def worker(i):
            try:
                tracker.set(f"t{i}", i)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(n)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        # 验证所有值都被正确设置了
        for i in range(n):
            assert tracker.get(f"t{i}") == i, f"Missing or wrong value for t{i}"

    def test_rollback_records_in_history(self):
        """rollback 操作被记录到 history。"""
        tracker = ExplicitStateTracker("test_rollback_hist")
        cp1 = tracker.checkpoint()
        tracker.set("x", 5)
        tracker.rollback(cp1)
        hist = tracker.history()
        rollback_events = [h for h in hist if h["type"] == "rollback"]
        assert len(rollback_events) >= 1
        assert rollback_events[0]["checkpoint_id"] == cp1

    def test_set_updates_value(self):
        """重复 set 同一个 key 会更新值。"""
        tracker = ExplicitStateTracker("test_update")
        tracker.set("key", "old")
        tracker.set("key", "new")
        assert tracker.get("key") == "new"
        hist = tracker.history(key="key")
        # 最近的 set 是 'new'
        assert hist[0]["value"] == "new"
        assert hist[0]["old_value"] == "old"
