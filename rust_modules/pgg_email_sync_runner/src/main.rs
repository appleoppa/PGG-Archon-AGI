use chrono::{Local, SecondsFormat};
use serde_json::json;
use std::{env, fs, path::PathBuf, process::Command};

fn home() -> PathBuf {
    PathBuf::from(env::var("HOME").unwrap_or_else(|_| "/Users/appleoppa".to_string()))
}

fn main() {
    let h = home();
    let hermes = h.join(".hermes");
    let out_root = hermes.join("workspace/pgg-archon-governance/email-memory-sync-auto");
    fs::create_dir_all(&out_root).ok();
    let force_send = env::var("PGG_EMAIL_SYNC_FORCE").ok().as_deref() == Some("1")
        || env::args().any(|a| a == "--force-send");
    let script = r#"
from pathlib import Path
import json, datetime, zipfile, ssl, smtplib, email.message, subprocess, hashlib, os
HOME=Path('/Users/appleoppa')
EMAIL='61079425@qq.com'
SVC='hermes-qq-mail-smtp'
ROOT=HOME/'.hermes/workspace/pgg-archon-governance/email-memory-sync-auto'
FORCE=os.environ.get('PGG_EMAIL_SYNC_FORCE')=='1'
stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
today=datetime.datetime.now(datetime.timezone.utc).astimezone().date().isoformat()
outdir=ROOT/stamp
outdir.mkdir(parents=True, exist_ok=True)
files=[]
for p in [
 HOME/'.hermes/skills/workflow/memory-retrieval-architecture/references/feishu-memory-root-cure-three-layer-20260618.md',
 HOME/'.hermes/skills/email/himalaya/references/feishu-email-sync-governance-20260618.md',
 HOME/'.hermes/workspace/pgg-archon-governance/email-sync-governance-gate/latest.json',
 HOME/'.hermes/workspace/pgg-archon-governance/feishu-doc-comparison-20260618-R8dL/LOCAL_COMPARISON_REPORT.md',
 HOME/'.hermes/workspace/pgg-archon-governance/feishu-doc-comparison-20260618-NsZ2/LOCAL_COMPARISON_REPORT.md',
]:
    if p.exists(): files.append(p)
readme=outdir/'README.md'
readme.write_text('# PGG/Hermes 自动邮箱同步包（脱敏）\n\n生成时间：%s\n目标邮箱：%s\n模式：daily controlled sync with idempotency guard\n\n## 边界\n- 不含案件材料、密钥、config.yaml、MEMORY.md/USER.md 原文、数据库、原始飞书全文。\n- 只含治理 reference、对照报告、gate latest。\n- 若附件超过 50KB，本 runner 拒绝发送。\n- 同一天已成功发送时，默认跳过；只有 PGG_EMAIL_SYNC_FORCE=1 或 --force-send 才强制重发。\n' % (datetime.datetime.now(datetime.timezone.utc).isoformat(), EMAIL))
zip_path=outdir/('pgg-memory-governance-auto-sync-%s.zip' % stamp)
with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED) as z:
    z.write(readme,'README.md')
    for p in files:
        safe_name = str(p).replace(str(HOME/'.hermes/'), '').replace('/', '__')
        z.write(p, safe_name)
size=zip_path.stat().st_size
if size > 50000:
    raise SystemExit('ATTACHMENT_TOO_LARGE %s' % size)
sha256=hashlib.sha256(zip_path.read_bytes()).hexdigest()

def load_json_lines(path):
    if not path.exists():
        return []
    out=[]
    for line in path.read_text(errors='ignore').splitlines():
        line=line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except Exception:
            pass
    return out

def sent_date(receipt):
    ts=receipt.get('sent_at') or receipt.get('generated_at') or ''
    if not ts:
        return None
    try:
        return datetime.datetime.fromisoformat(ts.replace('Z','+00:00')).astimezone().date().isoformat()
    except Exception:
        return ts[:10]

latest_path=ROOT/'latest.json'
ledger_path=ROOT/'ledger.jsonl'
prior=[]
if latest_path.exists():
    try: prior.append(json.loads(latest_path.read_text()))
    except Exception: pass
prior += load_json_lines(ledger_path)
# Hard idempotency: one successful SMTP send per local day unless explicitly forced.
already_today=[r for r in prior if str(r.get('status','')).startswith('PASS_SENT') and sent_date(r)==today]
# Secondary dedupe: if the same package hash was sent before, skip unless forced.
same_hash=[r for r in prior if str(r.get('status','')).startswith('PASS_SENT') and r.get('attachment_sha256')==sha256]
if not FORCE and (already_today or same_hash):
    reason='SKIPPED_ALREADY_SENT_TODAY' if already_today else 'SKIPPED_DUPLICATE_ATTACHMENT_HASH'
    basis=already_today[-1] if already_today else same_hash[-1]
    receipt={
      'status':'PASS_'+reason,
      'to':EMAIL,'from':EMAIL,'smtp_host':'smtp.qq.com','smtp_port':465,
      'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'attachment':str(zip_path),'attachment_size':size,'attachment_sha256':sha256,
      'previous_sent_at':basis.get('sent_at'),
      'previous_attachment':basis.get('attachment'),
      'force_required':'PGG_EMAIL_SYNC_FORCE=1 or --force-send',
      'boundary':['no smtp send on duplicate','no secret printed','no MEMORY_USER raw','no config.yaml','no case files','daily idempotency guard']
    }
    (outdir/'email_send_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2))
    latest_path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2))
    with ledger_path.open('a') as f: f.write(json.dumps(receipt,ensure_ascii=False)+'\n')
    print(json.dumps(receipt,ensure_ascii=False))
    raise SystemExit(0)

auth=subprocess.check_output(['security','find-generic-password','-a',EMAIL,'-s',SVC,'-w'], text=True).strip()
msg=email.message.EmailMessage()
msg['From']=EMAIL
msg['To']=EMAIL
msg['Subject']='PGG/Hermes 自动记忆治理同步包（脱敏）'
msg.set_content('苹果哥，这是 PGG/Hermes 自动邮箱同步包（脱敏小附件）。\n\n生成时间：%s\n附件：%s\n\n边界：不含案件材料、密钥、config.yaml、MEMORY/USER 原文、数据库或原始飞书全文。\n' % (datetime.datetime.now().isoformat(), zip_path.name))
msg.add_attachment(zip_path.read_bytes(), maintype='application', subtype='zip', filename=zip_path.name)
with smtplib.SMTP_SSL('smtp.qq.com',465,context=ssl.create_default_context(),timeout=30) as s:
    s.login(EMAIL, auth)
    s.send_message(msg)
receipt={
 'status':'PASS_SENT_SMTP_SSL_AUTO','to':EMAIL,'from':EMAIL,'smtp_host':'smtp.qq.com','smtp_port':465,
 'sent_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'attachment':str(zip_path),'attachment_size':size,
 'attachment_sha256':sha256,
 'force_send':FORCE,
 'boundary':['no secret printed','no MEMORY_USER raw','no config.yaml','no case files','daily idempotency guard']
}
(outdir/'email_send_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2))
latest_path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2))
with ledger_path.open('a') as f: f.write(json.dumps(receipt,ensure_ascii=False)+'\n')
print(json.dumps(receipt,ensure_ascii=False))
"#;
    let mut command = Command::new("/usr/bin/python3");
    command.arg("-c").arg(script);
    if force_send {
        command.env("PGG_EMAIL_SYNC_FORCE", "1");
    }
    let output = command.output();
    let (status, stdout, stderr, code) = match output {
        Ok(o) => (
            if o.status.success() { "PASS" } else { "WATCH" },
            String::from_utf8_lossy(&o.stdout).to_string(),
            String::from_utf8_lossy(&o.stderr).to_string(),
            o.status.code().unwrap_or(-1),
        ),
        Err(e) => ("BLOCKED", String::new(), e.to_string(), -1),
    };
    let result = json!({
        "schema":"pgg-email-sync-runner/v2",
        "generated_at": Local::now().to_rfc3339_opts(SecondsFormat::Secs, true),
        "status": status,
        "exit_code": code,
        "force_send": force_send,
        "stdout": stdout,
        "stderr_tail": stderr.chars().rev().take(2000).collect::<String>().chars().rev().collect::<String>(),
        "boundary":["daily idempotency guard", "duplicate hash guard", "sanitized package only", "keychain credential", "no memory/user raw", "no case/config payload"]
    });
    let latest = out_root.join("runner_latest.json");
    fs::write(&latest, serde_json::to_string_pretty(&result).unwrap()).unwrap();
    let mut ledger = fs::OpenOptions::new().create(true).append(true).open(out_root.join("runner_ledger.jsonl")).unwrap();
    use std::io::Write;
    writeln!(ledger, "{}", serde_json::to_string(&result).unwrap()).ok();
    println!("{}", serde_json::to_string(&result).unwrap());
    if status != "PASS" { std::process::exit(2); }
}
