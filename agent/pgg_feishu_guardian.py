#!/usr/bin/env python3
"""PGG Feishu Recovery Guardian — 飞书恢复守护。

架构：
  ┌──────────────┐     ┌────────────────┐     ┌──────────────┐
  │ Hermes Agent │────▶│ Recovery Guard │────▶│ .bak 文件库   │
  │ (Python)     │     │ (备份/回滚)     │     │              │
  └──────┬───────┘     └────────────────┘     └──────────────┘
         │ 崩溃了
         ▼
  ┌──────────────────────────────────────┐
  │  pgg_feishu_guardian (独立Python进程)  │
  │  • 心跳检测（每10秒）                  │
  │  • 飞书消息轮询（每5秒）               │
  │  • 恢复执行（回滚/重启/修复）           │
  └──────────────────────────────────────┘
         ▲
         │ 你在飞书发 "修复" "回滚" "状态"
         │
  ┌──────┴───────┐
  │    飞书Bot    │
  └──────────────┘

工作模式：
  1. 正常：Hermes 活着 → 只心跳检测 + 飞书消息轮询
  2. 告警：心跳超时 → 飞书发告警 + 等你的修复命令
  3. 恢复：收到 "回滚" / "修复" / "重启" → 执行恢复
  4. 自恢复：心跳超时 >300秒 → 自动回滚最近备份并重启 Hermes

依赖：Python 3.9+，标准库 + requests（已有）
权限：不需要 Hermes 运行
启动：独立的 launchd 服务
"""

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

# ─── 配置 ───

HERMES_HOME = Path(os.path.expanduser("~/.hermes"))
HERMES_AGENT = HERMES_HOME / "hermes-agent"
RECOVERY_DIR = HERMES_HOME / "workspace" / "pgg-recovery"
LEDGER_FILE = RECOVERY_DIR / "recovery_ledger.jsonl"
CONFIG_PATH = HERMES_HOME / "config.yaml"
ENV_PATH = HERMES_HOME / ".env"
HEARTBEAT_FILE = HERMES_HOME / "workspace" / "pgg-recovery" / "heartbeat.json"
GENE_DB = HERMES_HOME / "workspace" / "04_knowledge" / "开智" / "02-进化基因" / "apex_evolution_genes.sqlite3"

# 飞书
FEISHU_APP_ID = ""
FEISHU_APP_SECRET = ""      # 从 .env 读取
FEISHU_BASE = "https://open.feishu.cn/open-apis"

# 阈值
HEARTBEAT_TIMEOUT = 120       # 心跳超时秒数 → 进入 WATCH 状态
AUTO_RECOVER_TIMEOUT = 300    # 超过此秒数自动回滚重启
HEARTBEAT_CHECK_INTERVAL = 10  # 心跳检查间隔
FEISHU_POLL_INTERVAL = 5       # 飞书消息轮询间隔

# 受保护路径前缀（不允许修改）
PROTECTED_PREFIXES = [
    str(HERMES_HOME / "hermes-agent" / "agent" / "pgg_feishu_guardian.py"),
    str(HERMES_HOME / ".env"),
    str(HERMES_HOME / "config.yaml"),
]


# ─── 状态 ───

status = {
    "mode": "unknown",
    "hermes_alive": False,
    "last_heartbeat": 0,
    "last_feishu_check": 0,
    "feishu_connected": False,
    "recovery_attempted": False,
    "last_recovery": "",
    "uptime": 0,
    "started_at": time.time(),
}


def _log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def _read_env() -> dict[str, str]:
    """从 .env 读取飞书凭证。"""
    global FEISHU_APP_ID, FEISHU_APP_SECRET
    env = {}
    try:
        with open(ENV_PATH) as f:
            for line in f:
                s = line.strip()
                if s and not s.startswith("#") and "=" in s:
                    k, v = s.split("=", 1)
                    env[k.strip()] = v.strip().strip("'\"")
        FEISHU_APP_ID = env.get("FEISHU_APP_ID", "")
        FEISHU_APP_SECRET = env.get("FEISHU_APP_SECRET", "")
        return env
    except Exception as e:
        _log(f"❌ 读取.env失败: {e}")
        return {}


# ─── 心跳 ───


def check_heartbeat() -> dict[str, Any]:
    """检查 Hermes 心跳 + 进程 + 端口。"""
    result = {"alive": False, "heartbeat_age": -1, "process_running": False, "details": {}}

    # 1. 心跳文件
    try:
        if HEARTBEAT_FILE.exists():
            hb = json.loads(HEARTBEAT_FILE.read_text())
            ts = hb.get("timestamp", 0)
            age = time.time() - ts
            result["heartbeat_age"] = round(age, 1)
            result["details"]["heartbeat"] = hb
    except Exception:
        result["heartbeat_age"] = -2

    # 2. Hermes 进程
    try:
        ps = subprocess.run(
            ["pgrep", "-f", "hermes-agent|run_agent|hermes"],
            capture_output=True, text=True, timeout=5,
        )
        result["process_running"] = ps.returncode == 0 and bool(ps.stdout.strip())
    except Exception:
        result["process_running"] = False

    # 3. 综合判断
    hb_ok = result["heartbeat_age"] >= 0 and result["heartbeat_age"] < HEARTBEAT_TIMEOUT
    proc_ok = result["process_running"]
    result["alive"] = hb_ok or proc_ok

    return result


def write_heartbeat():
    """Hermes 调用此函数写入心跳（由 self_evolution_loop 周期调用）。"""
    HEARTBEAT_FILE.parent.mkdir(parents=True, exist_ok=True)
    hb = {
        "timestamp": time.time(),
        "pid": os.getpid(),
        "host": os.uname().nodename,
        "version": "pgg_feishu_guardian/v1",
    }
    HEARTBEAT_FILE.write_text(json.dumps(hb))
    return hb


# ─── 飞书 ───


def feishu_get_tenant_token() -> Optional[str]:
    """获取飞书 tenant_access_token。"""
    if not FEISHU_APP_ID or not FEISHU_APP_SECRET:
        _log("❌ 飞书凭证缺失")
        return None
    try:
        r = subprocess.run(
            ["curl", "-s", "-m", "10",
             "-X", "POST", f"{FEISHU_BASE}/auth/v3/tenant_access_token/internal",
             "-H", "Content-Type: application/json",
             "-d", json.dumps({
                 "app_id": FEISHU_APP_ID,
                 "app_secret": FEISHU_APP_SECRET,
             })],
            capture_output=True, text=True, timeout=15,
        )
        resp = json.loads(r.stdout)
        token = resp.get("tenant_access_token")
        if token:
            return token
        _log(f"❌ 飞书 token 失败: {resp.get('msg', r.stdout[:100])}")
        return None
    except Exception as e:
        _log(f"❌ 飞书 token 异常: {e}")
        return None


def feishu_send_message(token: str, receive_id: str, content: str, msg_type: str = "text") -> bool:
    """通过飞书 bot 发送消息。"""
    payload = {
        "receive_id": receive_id,
        "msg_type": msg_type,
        "content": json.dumps({"text": content}),
    }
    try:
        r = subprocess.run(
            ["curl", "-s", "-m", "10",
             "-X", "POST", f"{FEISHU_BASE}/im/v1/messages?receive_id_type=open_id",
             "-H", "Authorization: Bearer " + token,
             "-H", "Content-Type: application/json",
             "-d", json.dumps(payload)],
            capture_output=True, text=True, timeout=15,
        )
        resp = json.loads(r.stdout)
        if resp.get("code") == 0:
            return True
        _log(f"❌ 飞书发送失败: code={resp.get('code')} msg={resp.get('msg','')}")
        return False
    except Exception as e:
        _log(f"❌ 飞书发送异常: {e}")
        return False


def feishu_find_group(token: str) -> Optional[str]:
    """查找飞书群聊 ID（发给群消息）。"""
    try:
        # 尝试群列表
        r = subprocess.run(
            ["curl", "-s", "-m", "10",
             "-H", "Authorization: Bearer " + token,
             f"{FEISHU_BASE}/im/v1/chats?page_size=20"],
            capture_output=True, text=True, timeout=15,
        )
        resp = json.loads(r.stdout)
        if resp.get("code") == 0:
            items = resp.get("data", {}).get("items", [])
            for chat in items:
                name = chat.get("name", "")
                # 匹配包含 Hermes/PGG/苹果 的群
                if any(k in name for k in ["Hermes", "PGG", "苹果", "AI", "进化"]):
                    _log(f"📨 找到目标群: {name} ({chat['chat_id']})")
                    return chat["chat_id"]
            if items:
                # 返回第一个非私聊群
                for chat in items:
                    if chat.get("chat_type") == "group":
                        _log(f"📨 使用第一个群: {chat.get('name','?')} ({chat['chat_id']})")
                        return chat["chat_id"]
        return None
    except Exception as e:
        _log(f"❌ 飞书群查询异常: {e}")
        return None


def feishu_poll_messages(token: str, last_msg_id: str = "") -> list[dict[str, Any]]:
    """轮询飞书 bot 收到的消息。"""
    try:
        r = subprocess.run(
            ["curl", "-s", "-m", "10",
             "-H", "Authorization: Bearer " + token,
             f"{FEISHU_BASE}/im/v1/messages?page_size=20&sort_type=ByCreateTimeDesc"],
            capture_output=True, text=True, timeout=15,
        )
        resp = json.loads(r.stdout)
        if resp.get("code") != 0:
            return []
        items = resp.get("data", {}).get("items", [])
        new_msgs = []
        for msg in items:
            mid = msg.get("message_id", "")
            if mid == last_msg_id:
                break
            msg_type = msg.get("msg_type", "")
            if msg_type == "text":
                try:
                    body = json.loads(msg.get("body", {}).get("content", "{}"))
                    text = body.get("text", "")
                    sender = msg.get("sender", {}).get("id", "")
                    new_msgs.append({
                        "id": mid,
                        "text": text,
                        "sender": sender,
                        "time": msg.get("create_time", ""),
                    })
                except Exception:
                    pass
        return new_msgs
    except Exception as e:
        _log(f"❌ 飞书消息轮询异常: {e}")
        return []


# ─── 恢复 ───


def find_backup(path: str, since: float = 0) -> Optional[Path]:
    """找最近的备份文件。"""
    safe_name = path.replace("/", "_").replace("~", "home").replace(".", "_")
    candidates = list(RECOVERY_DIR.glob(f"{safe_name}*"))
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    for c in candidates:
        if c.stat().st_mtime >= since:
            return c
    return candidates[0] if candidates else None


def do_rollback(path: str) -> dict[str, Any]:
    """执行回滚到最近备份。"""
    bak = find_backup(path)
    if not bak:
        return {"error": f"没有找到 {path} 的备份", "rolled_back": False}

    # 读取校验
    bak_bytes = bak.read_bytes()
    bak_sha = hashlib.sha256(bak_bytes).hexdigest()

    # 备份当前（崩前保护）
    dest = Path(os.path.expanduser(path))
    if dest.exists():
        pre_bak = RECOVERY_DIR / f"pre_rollback.{int(time.time())}.bak"
        shutil.copy2(str(dest), str(pre_bak))

    # 恢复
    shutil.copy2(str(bak), str(dest))

    # 校验
    restored_sha = hashlib.sha256(dest.read_bytes()).hexdigest()
    if restored_sha != bak_sha:
        return {"error": "sha256校验失败", "rolled_back": False}

    return {
        "rolled_back": True,
        "restored_from": str(bak),
        "sha256": bak_sha,
    }


def do_restart_hermes() -> dict[str, Any]:
    """重启 Hermes launchd 服务。"""
    cmds = [
        "launchctl kickstart gui/501/ai.hermes.pgg-self-evolution-loop",
        "launchctl kickstart gui/501/ai.hermes.pgg-batch-evolution-scheduler",
        "launchctl kickstart gui/501/ai.hermes.pgg-autonomy-default-loop",
    ]
    results = []
    for cmd in cmds:
        try:
            r = subprocess.run(cmd.split(), capture_output=True, text=True, timeout=10)
            results.append({"cmd": cmd, "exit": r.returncode, "out": r.stdout[:100]})
        except Exception as e:
            results.append({"cmd": cmd, "error": str(e)})
    return {"restarted": True, "results": results}


def do_status_report() -> dict[str, Any]:
    """生成完整状态报告。"""
    hb = check_heartbeat()
    backups = list(RECOVERY_DIR.glob("*.bak"))
    backups.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    # 检查 GeneDB
    gene_stats = {}
    try:
        db = sqlite3.connect(str(GENE_DB))
        gene_stats["total"] = db.execute("SELECT COUNT(*) FROM evolution_genes").fetchone()[0]
        gene_stats["verified"] = db.execute("SELECT COUNT(*) FROM evolution_genes WHERE status='verified'").fetchone()[0]
        gene_stats["active"] = db.execute("SELECT COUNT(*) FROM evolution_genes WHERE status='active'").fetchone()[0]
        gene_stats["candidate"] = db.execute("SELECT COUNT(*) FROM evolution_genes WHERE status='candidate'").fetchone()[0]
        db.close()
    except Exception:
        gene_stats = {"error": "GeneDB不可读"}

    # 最近 ledger
    recent_ledger = []
    try:
        with open(LEDGER_FILE) as f:
            lines = f.readlines()[-5:]
        for l in lines:
            try:
                recent_ledger.append(json.loads(l))
            except Exception:
                pass
    except Exception:
        pass

    return {
        "status": "alive" if hb["alive"] else "down" if hb["heartbeat_age"] > AUTO_RECOVER_TIMEOUT else "watch",
        "hermes": hb,
        "guardian_uptime": round(time.time() - status["started_at"], 1),
        "backup_count": len(backups),
        "gene_db": gene_stats,
        "recent_ledger": recent_ledger[-3:],
        "config_exists": CONFIG_PATH.exists(),
    }


def handle_feishu_command(text: str, token: str, chat_id: str) -> str:
    """处理飞书收到的命令。"""
    cmd = text.strip().lower()

    if "状态" in cmd or "status" in cmd:
        report = do_status_report()
        alive = "✅ **正常运行**" if report["hermes"]["alive"] else "❌ **已崩溃**"
        hb_age = report["hermes"].get("heartbeat_age", -1)
        reply = (
            f"🤖 **PGG飞书守护状态**\n"
            f"{alive}\n"
            f"守护运行: {report['guardian_uptime']}s\n"
            f"心跳: {hb_age}s前\n"
            f"进程: {'✅' if report['hermes'].get('process_running') else '❌'} 运行\n"
            f"备份: {report['backup_count']} 份\n"
            f"基因库: ver={report['gene_db'].get('verified','?')} active={report['gene_db'].get('active','?')}\n"
            f"Config: {'✅' if report['config_exists'] else '❌'}"
        )
        feishu_send_message(token, chat_id, reply)
        return reply

    if "回滚" in cmd or "rollback" in cmd:
        # 解析回滚哪个文件
        target_path = str(CONFIG_PATH)  # 默认回滚 config.yaml
        for kw, path in [
            ("config", CONFIG_PATH),
            (".env", ENV_PATH),
            ("recovery", HERMES_HOME / "hermes-agent" / "agent" / "pgg_recovery_guard.py"),
        ]:
            if kw in cmd:
                target_path = str(path)
                break

        result = do_rollback(target_path)
        if result.get("rolled_back"):
            reply = f"✅ 回滚成功: {target_path}\n  来源: {result['restored_from']}"
        else:
            reply = f"❌ 回滚失败: {result.get('error', '未知错误')}"
        feishu_send_message(token, chat_id, reply)
        return reply

    if "重启" in cmd or "restart" in cmd:
        result = do_restart_hermes()
        reply = f"🔄 Hermes 重启结果:\n"
        for r in result["results"]:
            rc = r.get("exit", r.get("error", "?"))
            reply += f"  {r['cmd'][:60]} → {rc}\n"
        feishu_send_message(token, chat_id, reply)
        return reply

    if "修复" in cmd or "fix" in cmd or "recover" in cmd:
        # 自动修复流程：回滚 config → 重启
        results = []
        rb = do_rollback(str(CONFIG_PATH))
        results.append(f"config回滚: {'✅' if rb.get('rolled_back') else '❌' + rb.get('error','?')}")
        rst = do_restart_hermes()
        for r in rst["results"]:
            results.append(f"重启: {r['cmd'][:40]} exit={r.get('exit','?')}")
        reply = "🛠 **自动修复**\n" + "\n".join(results)
        feishu_send_message(token, chat_id, reply)
        return reply

    # 默认
    reply = (
        f"🤖 收到命令: {text}\n"
        f"支持的命令:\n"
        f"  `状态` — 查看系统状态\n"
        f"  `回滚 config` — 回滚 config.yaml\n"
        f"  `回滚 .env` — 回滚环境变量\n"
        f"  `重启` — 重启 Hermes 服务\n"
        f"  `修复` — 自动回滚+重启\n"
        f"  `status` — English status report"
    )
    feishu_send_message(token, chat_id, reply)
    return reply


# ─── 主循环 ───


def main_loop(mode: str = "watchdog", chat_id: str = ""):
    """守护主循环。"""
    _log(f"🚀 PGG 飞书守护启动 (mode={mode})")
    _read_env()

    last_msg_id = ""
    feishu_token = None
    feishu_chat_id = chat_id

    # 写入初始心跳
    write_heartbeat()
    status["mode"] = mode
    status["last_heartbeat"] = time.time()

    while True:
        try:
            # 1. 心跳检查
            hb = check_heartbeat()
            status["hermes_alive"] = hb["alive"]
            hb_age = hb.get("heartbeat_age", -1)

            # 2. 每60秒写一次自己的心跳
            if time.time() - status["last_heartbeat"] > 60:
                write_heartbeat()
                status["last_heartbeat"] = time.time()

            # 3. 飞书连接（每300秒刷新 token）
            if mode == "server" and (feishu_token is None or time.time() - status["last_feishu_check"] > 300):
                feishu_token = feishu_get_tenant_token()
                status["feishu_connected"] = feishu_token is not None
                if feishu_token and not feishu_chat_id:
                    feishu_chat_id = feishu_find_group(feishu_token) or chat_id
                    status["last_feishu_check"] = time.time()

            # 4. 飞书消息轮询
            if mode == "server" and feishu_token and feishu_chat_id:
                msgs = feishu_poll_messages(feishu_token, last_msg_id)
                for msg in msgs:
                    _log(f"📨 收到飞书消息: {msg['text'][:60]}")
                    handle_feishu_command(msg["text"], feishu_token, feishu_chat_id)
                    if msg["id"]:
                        last_msg_id = msg["id"]

            # 5. 告警：心跳超时但未崩溃
            if hb_age > HEARTBEAT_TIMEOUT and not status.get("recovery_attempted") and mode == "server" and feishu_token and feishu_chat_id:
                _log(f"⚠️ Hermes 心跳超时 {hb_age}s → 发送飞书告警")
                feishu_send_message(
                    feishu_token, feishu_chat_id,
                    f"⚠️ **Hermes 告警**\n心跳停止 {hb_age}s\n进程: {'✅' if hb['process_running'] else '❌'}\n发送 `修复` 自动恢复"
                )
                status["recovery_attempted"] = True

            # 6. 自动恢复：超时太久且进程不在
            if hb_age > AUTO_RECOVER_TIMEOUT and not hb["process_running"] and mode == "server":
                _log(f"🔧 自动恢复触发: 心跳停止 {hb_age}s")
                rb = do_rollback(str(CONFIG_PATH))
                rst = do_restart_hermes()
                status["last_recovery"] = f"auto_recover_at_{time.time()}"
                _log(f"  回滚: {'✅' if rb.get('rolled_back') else '❌'} 重启: {len(rst.get('results',[]))} 条")
                if feishu_token and feishu_chat_id:
                    feishu_send_message(
                        feishu_token, feishu_chat_id,
                        f"🔧 **自动恢复执行**\n回滚: {'✅' if rb.get('rolled_back') else '❌'+rb.get('error','?')}\n重启: {'✅' if any(r.get('exit') == 0 for r in rst.get('results',[])) else '⚠️部分失败'}"
                    )
                # 等待1分钟后重置告警状态
                time.sleep(60)
                status["recovery_attempted"] = False

            # 7. 如果hermes恢复了，重置告警
            if hb["alive"] and status.get("recovery_attempted"):
                _log("✅ Hermes 已恢复，重置告警状态")
                status["recovery_attempted"] = False

            # 8. 间隔
            time.sleep(HEARTBEAT_CHECK_INTERVAL)

        except KeyboardInterrupt:
            _log("👋 守护退出")
            break
        except Exception as e:
            _log(f"❌ 主循环异常: {e}")
            time.sleep(10)


# ─── CLI ───


def main():
    parser = argparse.ArgumentParser(description="PGG 飞书恢复守护")
    parser.add_argument("--mode", choices=["watchdog", "server"], default="watchdog",
                        help="运行模式: watchdog=仅心跳检测, server=飞书消息+恢复")
    parser.add_argument("--chat-id", type=str, default="",
                        help="飞书群聊ID（server模式）")
    parser.add_argument("--heartbeat", action="store_true", help="写入一次心跳（由Hermes调用）")
    parser.add_argument("--status", action="store_true", help="显示状态报告")
    parser.add_argument("--rollback", type=str, nargs="?", const="~/.hermes/config.yaml",
                        help="回滚指定文件到最近备份")
    parser.add_argument("--restart", action="store_true", help="重启 Hermes 服务")
    parser.add_argument("--test-feishu", action="store_true", help="测试飞书连接")
    parser.add_argument("--daemon", action="store_true", help="后台守护模式（launchd）")

    args = parser.parse_args()

    if args.heartbeat:
        result = write_heartbeat()
        print(json.dumps(result))
        return

    if args.status:
        report = do_status_report()
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return

    if args.rollback:
        result = do_rollback(os.path.expanduser(args.rollback))
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    if args.restart:
        result = do_restart_hermes()
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    if args.test_feishu:
        _read_env()
        token = feishu_get_tenant_token()
        if token:
            print(f"✅ 飞书 token 获取成功 (前20: {token[:20]}...)")
            chat = feishu_find_group(token)
            if chat:
                print(f"✅ 找到群: {chat}")
                ok = feishu_send_message(token, chat, "🧪 PGG 飞书守护测试消息")
                print(f"{'✅' if ok else '❌'} 消息发送")
            else:
                print("❌ 未找到群")
        else:
            print("❌ 飞书 token 获取失败")
        return

    if args.daemon:
        main_loop(mode=args.mode, chat_id=args.chat_id)
        return

    parser.print_help()


if __name__ == "__main__":
    main()