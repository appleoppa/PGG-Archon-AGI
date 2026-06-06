# 全局重编号修复模式

来源：2026-06-05 会话，PGG-MS-20260605-0001→0005 重编号

## 触发场景

案件编号的序号段分配错误（如用了 0001 但全局已有 0001-0004），需要整体重编号。

## 修复步骤

### 1. 查清已有案件

```bash
find ~/.hermes/workspace -maxdepth 3 -type d | grep -E '[0-9]{4}-PGGMS' | sort
```

输出形如：
```
.../0001-PGGMS-20260601-汇金热力有限公司合同审阅
.../0002-PGGMS-20260601-堂弟离婚及彩礼返还纠纷
.../0003-PGGMS-20260531-尚永恒+工伤待遇争议
.../0004-PGGMS-20260601-原阳县汇金热力有限公司+电信服务合同审阅
```

最高序号 = 0004 → 新案 = 0005

### 2. 重命名顶级目录

```bash
mv "0001-PGGMS-YYYYMMDD-当事人" "0005-PGGMS-YYYYMMDD-当事人"
```

### 3. 重命名 stage 子目录（含中文）

⚠ **不能用 shell `mv`直接操作含有中文括号的目录名**（Illegal byte sequence）。必须用 Python：

```python
import os
base = os.path.expanduser("~/.../新目录")
for d in os.listdir(base):
    if os.path.isdir(os.path.join(base, d)) and "PGG-MS-YYYYMMDD-0001" in d:
        new_d = d.replace("PGG-MS-YYYYMMDD-0001", "PGG-MS-YYYYMMDD-0005")
        os.rename(os.path.join(base, d), os.path.join(base, new_d))
```

### 4. 批量替换文件内容

所有 `.md` 文件中引用的旧编号（如 `PGG-MS-YYYYMMDD-0001` 和 `0001-PGGMS-YYYYMMDD-`）需要同步更新：

```python
import os
base = "..."
for root, dirs, files in os.walk(base):
    for f in files:
        if not f.endswith(".md"):
            continue
        fp = os.path.join(root, f)
        with open(fp, "r") as fh:
            content = fh.read()
        content = content.replace("PGG-MS-YYYYMMDD-0001", "PGG-MS-YYYYMMDD-0005")
        content = content.replace("0001-PGGMS-YYYYMMDD-", "0005-PGGMS-YYYYMMDD-")
        with open(fp, "w") as fh:
            fh.write(content)
```

### 5. 更新台账

`case_ledger.json` 中对应条目的 case_number、directory、full_path、files 均需更新。

### 6. 终验

```bash
grep -rn "旧编号" ~/.hermes/workspace/新目录/  # 应为空
```

## Pitfalls

- 目录名含中文括号（`（一审）`）时，shell 的 `mv` 可能失败，必须用 Python `os.rename()`
- 文件内容中的编号引用可能有多处（YAML frontmatter、表格、正文），不要只改第一处
- `case_ledger.json` 中的 `directory` 和 `full_path` 也要同步更新
- 巡视组报告/审计组报告中引用旧编号的判断记录可以保留（描述历史），但路径引用必须修正
