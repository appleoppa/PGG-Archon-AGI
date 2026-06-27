#!/bin/bash
# APEX后处理修复脚本
# 在每次Evolver运行后自动修复新写入记录的缺失字段
# 用法: ./post-evolver-fix.sh

echo "[APEX] 后处理修复开始..."

node -e "
const fs = require('fs');

const files = [
  { path: '/root/.nvm/assets/gep/candidates.jsonl', required: ['schema_version','id','ts'] },
  { path: '/root/.nvm/assets/gep/events.jsonl', required: ['schema_version','id','ts'] },
  { path: '/root/.nvm/assets/gep/genes.jsonl', required: ['schema_version','id','ts'] },
  { path: '/root/.nvm/memory/distiller_log.jsonl', required: ['schema_version','id','ts'] },
  { path: '/root/.nvm/memory/evolution/memory_graph.jsonl', required: ['schema_version'] },
];

let totalFixed = 0;

for (const {path, required} of files) {
  if (!fs.existsSync(path)) continue;
  const lines = fs.readFileSync(path, 'utf8').trim().split('\n');
  let fixed = 0;
  let out = [];
  for (const l of lines) {
    if (!l.trim()) { out.push(l); continue; }
    try {
      const o = JSON.parse(l);
      let mod = false;
      for (const f of required) {
        if (!o[f]) {
          o[f] = f === 'schema_version' ? '1.0' : 
                 (f === 'id' ? 'rec_'+Date.now()+'_'+Math.random().toString(36).substring(2,6) : new Date().toISOString());
          mod = true;
        }
      }
      if (mod) fixed++;
      out.push(JSON.stringify(o));
    } catch(e) { out.push(l); }
  }
  if (fixed > 0) {
    fs.writeFileSync(path, out.join('\n') + '\n');
    console.log('[APEX] ' + path + ': 修复 ' + fixed + ' 条');
  }
  totalFixed += fixed;
}

// Fix JSON files
const jsonFiles = [
  { path: '/root/.nvm/assets/gep/genes.json', type: 'GeneCollection' },
  { path: '/root/.nvm/memory/evolution/personality_state.json', type: 'PersonalityState' },
];

for (const {path, type} of jsonFiles) {
  if (!fs.existsSync(path)) continue;
  try {
    const o = JSON.parse(fs.readFileSync(path, 'utf8'));
    let fixed = 0;
    if (!o.schema_version) { o.schema_version = '1.0'; fixed++; }
    if (!o.type && type) { o.type = type; fixed++; }
    if (fixed > 0) {
      fs.writeFileSync(path, JSON.stringify(o, null, 2));
      console.log('[APEX] ' + path + ': 修复 ' + fixed + ' 字段');
      totalFixed += fixed;
    }
  } catch(e) {}
}

console.log('[APEX] 后处理修复完成: 共修复 ' + totalFixed + ' 处');
"

# 验证结果
cd /root/.nvm/standard && node validate-apex-schema.js 2>&1 | grep "SUMMARY"
