# 平台投递参考：微信 & 飞书

> 2026-05-17 验证记录 | 聚合交付链的 VIIc 环节

---

## 微信通道投递

### 通道确认清单

首次使用或怀疑通道异常时，按以下顺序检查：

1. **Gateway是否在运行** — `ps aux | grep gateway`
2. **Gateway日志中weixin连接状态** — `grep "weixin\|wechat" ~/.hermes/logs/gateway.log`
   - 期望：`✓ weixin connected`
   - 错误：`poll error (1/3): Server disconnected`（重连机制会在1/3次后恢复）
3. **配对状态** — 检查 `~/.hermes/pairing/weixin-approved.json` 有用户ID
4. **Context tokens** — `~/.hermes/weixin/accounts/` 下应有 `*.context-tokens.json`
5. **微信客户端** — WeChat.app 需保持前台或后台登录状态
6. **历史错误** — 确认没有持续性的 `Unauthorized user` 警告（可能表示配对过期）

### 发送方法

通过 cronjob 一次性任务的 deliver 参数发送到微信：

```python
cronjob(
    action="create",
    schedule="1m",              # 1分钟后触发
    name="推送描述-验证",
    prompt="消息内容...直接输出，无需思考或回复",
    deliver="weixin:<用户ID>",   # 目标微信用户，如 "weixin:o9cq8082X2N3uObt001_mYHcwK0Y@im.wechat"
    repeat=1                    # 一次性
)
```

如需立即触发，先创建再 `cronjob(action="run", job_id="...")` 推到下一 scheduler tick。

### 验证送达

发送后检查 gateway.log：

```
2026-05-17 12:38:57,500 INFO cron.scheduler: Job 'xxx' completed successfully
2026-05-17 12:38:57,507 INFO cron.scheduler: Output saved to: /Users/appleoppa/.hermes/cron/output/<job_id>/<timestamp>.md
2026-05-17 12:38:59,928 INFO cron.scheduler: Job '<job_id>': delivered to weixin:<用户ID>
```

Cron输出文件记录了实际发送的内容，可用于核对。

### 限制

- 微信 bot 通道仅支持文字消息，不支持文件/图片/附件
- 依赖微信桌面客户端保持登录状态
- 消息内容不宜过长（微信单条消息有长度限制）
- 微信 bridge 通过 ilinkai.weixin.qq.com 连接，需保持网络通畅

---

## 飞书投递

与微信不同，飞书可通过 `scripts/feishu_delivery.py` 发送：

```bash
python3 scripts/feishu_delivery.py create <PGG编号> --title "文档标题"
python3 scripts/feishu_delivery.py fill <document_id> --content <报告路径>
python3 scripts/feishu_delivery.py check-env
```

飞书支持富文本、文档创建和内容填充，是正式交付的首选平台。

---

## 投递决策规则

| 场景 | 方式 | 命令/工具 |
|------|------|----------|
| 聚合交付到主库 | `cp -r` | 直接拷贝到 `~/苹果中枢办案库/` |
| 桌面同步副本 | `cp -r` | 拷贝到 `~/Desktop/苹果中枢办案库/` |
| 正式文档交付给苹果哥（飞书） | feishu_delivery.py | 按需执行，非自动 |
| 简短通知到手机（微信） | cron deliver | 按需执行，非自动 |
| 苹果哥主动询问进度 | 主会话内回复 | 即时回答，不发平台 |
