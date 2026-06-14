"""PGG Recovery Guard — 安全编辑/备份/验证/回滚模块。

授权（用户授权 2026-06-13）：
- 桥处理器可修配置文件 (.env, config.yaml)
- 可修改代码
- 可修config
- 但必须保证修崩了能恢复

保障机制：
1. 任何写操作前自动备份（带时间戳）
2. 写后自动验证（语法/格式/可达性）
3. 验证失败自动回滚
4. 每次操作记录到 recovery ledger
5. 人工可随时 rollback
"""

import json
import os
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

RECOVERY_DIR = Path(os.path.expanduser("~/.hermes/workspace/pgg-recovery"))
LEDGER_FILE = RECOVERY_DIR / "recovery_ledger.jsonl"


def _now() -> str:
    return datetime.now().isoformat()


def _ensure_dir():
    RECOVERY_DIR.mkdir(parents=True, exist_ok=True)


def _safe_name(path: str) -> str:
    """把文件路径转成安全的备份文件名。"""
    return path.replace("/", "_").replace("~", "home").replace(".", "_")


def _ledger_entry(entry: dict[str, Any]):
    """追加一行到 recovery ledger。"""
    _ensure_dir()
    entry["timestamp"] = _now()
    try:
        with open(LEDGER_FILE, "a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        pass  # ledger 写失败不能阻断主流程


# ─── 备份 ───


def backup_file(path: str, tag: str = "") -> dict[str, Any]:
    """备份文件到 recovery 目录。

    Args:
        path: 原始文件路径
        tag: 可选标签（如 "pre_config_fix", "pre_code_edit"）

    Returns: 备份元数据
    """
    _ensure_dir()
    src = Path(os.path.expanduser(path))

    if not src.exists():
        return {"error": f"文件不存在: {path}", "backed_up": False}

    # 先读内容做 checksum
    content_bytes = src.read_bytes()
    import hashlib
    sha256 = hashlib.sha256(content_bytes).hexdigest()
    ts = int(time.time())
    safe = _safe_name(str(src.resolve()))
    bak_name = f"{safe}.{ts}.bak"
    if tag:
        bak_name = f"{safe}.{tag}.{ts}.bak"
    bak_path = RECOVERY_DIR / bak_name

    shutil.copy2(str(src), str(bak_path))

    result = {
        "backed_up": True,
        "original": str(src.resolve()),
        "backup_path": str(bak_path),
        "backup_name": bak_name,
        "size": len(content_bytes),
        "sha256": sha256,
        "tag": tag or "auto",
    }
    _ledger_entry({"action": "backup", **result})
    return result


def list_backups(path: str) -> list[dict[str, Any]]:
    """列出某个文件的所有备份。"""
    _ensure_dir()
    safe = _safe_name(str(Path(os.path.expanduser(path)).resolve()))
    backups = []
    for f in sorted(RECOVERY_DIR.glob(f"{safe}*"), reverse=True):
        stat = f.stat()
        backups.append({
            "path": str(f),
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        })
    return backups


# ─── 回滚 ───


def rollback(path: str, backup_name: Optional[str] = None) -> dict[str, Any]:
    """从备份恢复文件。

    Args:
        path: 要恢复的原始文件路径
        backup_name: 指定备份名（默认用最新的，按 mtime 排序）

    Returns: 恢复结果
    """
    _ensure_dir()
    dest = Path(os.path.expanduser(path))
    safe = _safe_name(str(dest.resolve()))

    if backup_name:
        bak = RECOVERY_DIR / backup_name
        if not bak.exists():
            return {"error": f"备份文件不存在: {backup_name}", "rolled_back": False}
        # 验证备份属于该文件
        if not bak.name.startswith(safe):
            return {"error": f"备份 {backup_name} 不属于文件 {path}", "rolled_back": False}
    else:
        # 按 mtime 找最新备份
        all_baks = list(RECOVERY_DIR.glob(f"{safe}*"))
        all_baks.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        if not all_baks:
            return {"error": f"没有找到备份: {path}", "rolled_back": False}
        bak = all_baks[0]

    # 读取备份 sha256
    import hashlib
    bak_sha256 = hashlib.sha256(bak.read_bytes()).hexdigest()

    # 备份当前（崩溃前保护）
    pre_rollback = backup_file(path, tag="pre_rollback")

    # 恢复
    shutil.copy2(str(bak), str(dest))

    # 验证恢复结果
    restored_sha256 = hashlib.sha256(dest.read_bytes()).hexdigest()
    if restored_sha256 != bak_sha256:
        return {"error": f"恢复校验失败: sha256不匹配", "rolled_back": False}

    result = {
        "rolled_back": True,
        "restored_from": str(bak),
        "restored_to": str(dest.resolve()),
        "sha256": bak_sha256,
        "pre_rollback_backup": pre_rollback.get("backup_path", ""),
    }
    _ledger_entry({"action": "rollback", **result})
    return result


# ─── 验证器 ───


class VerifyError(Exception):
    pass


def verify_yaml(path: str) -> dict[str, Any]:
    """验证 YAML 文件语法。"""
    import yaml
    try:
        content = Path(os.path.expanduser(path)).read_text()
        yaml.safe_load(content)
        return {"valid": True, "format": "yaml"}
    except yaml.YAMLError as e:
        return {"valid": False, "error": str(e)}
    except Exception as e:
        return {"valid": False, "error": str(e)}


def verify_python(path: str) -> dict[str, Any]:
    """验证 Python 文件语法。"""
    try:
        content = Path(os.path.expanduser(path)).read_text()
        compile(content, path, "exec")
        return {"valid": True, "format": "python"}
    except SyntaxError as e:
        return {"valid": False, "error": str(e)}
    except Exception as e:
        return {"valid": False, "error": str(e)}


def verify_env(path: str) -> dict[str, Any]:
    """验证 .env 文件格式（每行 key=value 或注释/空行）。"""
    try:
        content = Path(os.path.expanduser(path)).read_text()
        errors = []
        for i, line in enumerate(content.splitlines(), 1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if "=" not in stripped:
                errors.append(f"Line {i}: 没有 '=' 分隔符: {stripped[:50]}")
        return {"valid": len(errors) == 0, "format": "env", "errors": errors}
    except Exception as e:
        return {"valid": False, "error": str(e)}


def verify_json(path: str) -> dict[str, Any]:
    """验证 JSON 文件格式。"""
    try:
        content = Path(os.path.expanduser(path)).read_text()
        json.loads(content)
        return {"valid": True, "format": "json"}
    except json.JSONDecodeError as e:
        return {"valid": False, "error": str(e)}
    except Exception as e:
        return {"valid": False, "error": str(e)}


VERIFIERS = {
    ".yaml": verify_yaml,
    ".yml": verify_yaml,
    ".py": verify_python,
    ".env": verify_env,
    ".json": verify_json,
}


def auto_verify(path: str) -> dict[str, Any]:
    """根据文件扩展名自动选择验证器。"""
    p = Path(os.path.expanduser(path))
    suffix = p.suffix.lower()
    verifier = VERIFIERS.get(suffix)
    if verifier:
        return verifier(path)
    # 未知类型 → 只检查文件可读
    try:
        p.read_bytes()
        return {"valid": True, "format": "unknown"}
    except Exception as e:
        return {"valid": False, "error": str(e)}


# ─── 安全编辑 ───


def safe_edit(
    path: str,
    old_string: str,
    new_string: str,
    tag: str = "edit",
    verify_func: Optional[Callable] = None,
) -> dict[str, Any]:
    """安全编辑文件：备份 → 编辑 → 验证 → 回滚失败。

    Args:
        path: 文件路径
        old_string: 要替换的旧文本
        new_string: 新文本
        tag: 操作标签
        verify_func: 自定义验证函数（默认 auto_verify）

    Returns: 操作结果
    """
    # 0. 路径白名单 — 只允许修改授权文件
    resolved_path = str(Path(os.path.expanduser(path)).resolve())
    _ALLOW_EDIT = [
        os.path.expanduser("~/.hermes/config.yaml"),
        os.path.expanduser("~/.hermes/.env"),
        os.path.expanduser("~/.hermes/workspace"),
        os.path.expanduser("~/.hermes/hermes-agent/agent"),
    ]
    allowed = False
    for ap in _ALLOW_EDIT:
        if resolved_path == ap or resolved_path.startswith(os.path.expanduser(ap) + "/"):
            allowed = True
            break
    if not allowed:
        return {
            "error": f"路径不在白名单: {path}",
            "edited": False,
            "allowed_prefixes": _ALLOW_EDIT,
        }

    # 1. 备份
    bak = backup_file(path, tag=f"pre_{tag}")
    if not bak.get("backed_up"):
        return {"error": "备份失败", "edited": False}

    # 2. 编辑
    fp = Path(os.path.expanduser(path))
    content = fp.read_text()

    if old_string not in content:
        return {
            "error": f"未找到匹配文本（前100字符: {old_string[:100]}）",
            "edited": False,
            "backup": bak["backup_path"],
        }

    new_content = content.replace(old_string, new_string, 1)
    fp.write_text(new_content)

    # 3. 验证
    verifier = verify_func or (lambda: auto_verify(path))
    try:
        v_result = verifier()
    except Exception as e:
        v_result = {"valid": False, "error": str(e)}

    if not v_result.get("valid"):
        # 验证失败 → 自动回滚
        roll = rollback(path, bak["backup_name"])
        return {
            "error": f"验证失败，已回滚: {v_result.get('error')}",
            "edited": False,
            "rolled_back": True,
            "verify_result": v_result,
            "rollback_result": roll,
        }

    # 4. 成功
    result = {
        "edited": True,
        "path": str(fp.resolve()),
        "backup": bak["backup_path"],
        "verify_result": v_result,
    }
    _ledger_entry({"action": "safe_edit", "tag": tag, **result})
    return result


def safe_write_env(key: str, value: str, path: str = "~/.hermes/.env", force: bool = False) -> dict[str, Any]:
    """安全的 .env 写入：备份 → 去重 → 替换/追加 → 验证。

    去重逻辑：先删除所有同名 key 行，再追加新行。
    这防止多次写入造成重复条目（已知 bugs 根源）。

    Args:
        key: 环境变量名
        value: 值
        path: .env 路径
        force: 是否强制写入受保护的 key（默认 False）

    Returns: 操作结果
    """
    fp = Path(os.path.expanduser(path))

    # 0. 保护锁：禁止意外覆盖关键密钥
    PROTECTED_KEYS = {"ARK_CODE_LATEST_API_KEY", "GPT55_5YUANTOKEN_API_KEY"}
    if key in PROTECTED_KEYS and not force:
        return {
            "written": False,
            "error": f"禁止覆盖受保护的 key '{key}'。如确需修改，请使用 force=True",
            "protected": True,
        }

    # 1. 备份
    bak = backup_file(path, tag="pre_env_write")
    if not bak.get("backed_up"):
        return {"error": "备份失败", "written": False}

    # 2. 读现有内容
    if fp.exists():
        content = fp.read_text()
        lines = content.splitlines(keepends=True)
    else:
        content = ""
        lines = []

    # 3. 去重：删除所有同名的已有条目
    cleaned_lines = []
    removed_count = 0
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            k = stripped.split("=", 1)[0].strip()
            if k == key:
                removed_count += 1
                continue  # 跳过：删除旧条目
        cleaned_lines.append(line)

    # 4. 追加新行
    if not content.endswith("\n") and cleaned_lines:
        cleaned_lines.append("\n")
    cleaned_lines.append(f"{key}={value}\n")

    new_content = "".join(cleaned_lines)

    # 5. 写回
    with open(fp, "w") as f:
        f.write(new_content)

    # 6. 验证
    v = verify_env(path)
    if not v.get("valid"):
        rollback(path, bak["backup_name"])
        return {
            "error": f"验证失败，已回滚: {v.get('errors', v.get('error'))}",
            "written": False,
            "rolled_back": True,
        }

    result = {
        "written": True,
        "key": key,
        "path": str(fp.resolve()),
        "action": "dedup_appended" if removed_count > 0 else "appended",
        "removed_duplicates": removed_count,
        "backup": bak["backup_path"],
        "verify_result": v,
    }
    _ledger_entry({"action": "safe_write_env", **result})
    return result


# ─── 安全重命名/移动 ───


def safe_move_file(src: str, dst: str, tag: str = "move") -> dict[str, Any]:
    """安全移动/重命名文件（先备份源文件）。"""
    bak = backup_file(src, tag=f"pre_{tag}")
    if not bak.get("backed_up"):
        return {"error": "备份失败", "moved": False}

    sp = Path(os.path.expanduser(src))
    dp = Path(os.path.expanduser(dst))
    dp.parent.mkdir(parents=True, exist_ok=True)

    shutil.move(str(sp), str(dp))

    result = {"moved": True, "from": str(sp), "to": str(dp), "backup": bak["backup_path"]}
    _ledger_entry({"action": "safe_move", "tag": tag, **result})
    return result


# ─── 命令行走廊 ───


def main():
    import argparse
    parser = argparse.ArgumentParser(description="PGG Recovery Guard — 安全编辑/备份/回滚")
    parser.add_argument("--backup", type=str, help="备份文件路径")
    parser.add_argument("--tag", type=str, default="manual", help="备份标签")
    parser.add_argument("--rollback", type=str, help="回滚文件路径")
    parser.add_argument("--backup-name", type=str, help="指定备份文件名（默认最新）")
    parser.add_argument("--list-backups", type=str, help="列出文件的备份")
    parser.add_argument("--verify", type=str, help="验证文件语法")
    parser.add_argument("--safe-edit", type=str, nargs=2, metavar=("OLD", "NEW"),
                        help="安全编辑文件 (需同时 --file)")
    parser.add_argument("--file", type=str, help="配合 --safe-edit 使用的文件路径")
    parser.add_argument("--env", type=str, nargs=2, metavar=("KEY", "VALUE"),
                        help="安全写入 .env 变量")
    parser.add_argument("--ledger", action="store_true", help="显示最近的 ledger 记录")
    parser.add_argument("--stats", action="store_true", help="显示备份统计")

    args = parser.parse_args()

    if args.backup:
        result = backup_file(args.backup, tag=args.tag)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    if args.list_backups:
        backups = list_backups(args.list_backups)
        if not backups:
            print(f"没有找到备份: {args.list_backups}")
        else:
            for b in backups:
                print(f"  [{b['modified']}] {b['path']} ({b['size']} bytes)")
        return

    if args.rollback:
        result = rollback(args.rollback, args.backup_name)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    if args.verify:
        result = auto_verify(args.verify)
        if result.get("valid"):
            print(f"✅ {args.verify} — 格式正确 ({result.get('format', '?')})")
        else:
            print(f"❌ {args.verify} — 错误: {result.get('error', result.get('errors', '?'))}")
        return

    if args.safe_edit and args.file:
        old, new = args.safe_edit
        result = safe_edit(args.file, old, new, tag=args.tag)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    if args.env:
        key, value = args.env
        result = safe_write_env(key, value)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    if args.ledger:
        try:
            with open(LEDGER_FILE) as f:
                lines = f.readlines()[-20:]
            for l in lines:
                try:
                    entry = json.loads(l)
                    print(f"  [{entry.get('timestamp', '?')}] {entry.get('action', '?')} — {entry.get('path', entry.get('original', entry.get('key', '?')))}")
                except json.JSONDecodeError:
                    continue
        except FileNotFoundError:
            print("ledger 为空")
        return

    if args.stats:
        _ensure_dir()
        files = list(RECOVERY_DIR.glob("*.bak"))
        sizes = [f.stat().st_size for f in files]
        print(f"备份目录: {RECOVERY_DIR}")
        print(f"备份文件数: {len(files)}")
        print(f"总大小: {sum(sizes):,} bytes")
        print(f"最大: {max(sizes):,} bytes" if sizes else "")
        print(f"最小: {min(sizes):,} bytes" if sizes else "")
        return

    parser.print_help()


if __name__ == "__main__":
    main()