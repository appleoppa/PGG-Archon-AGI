#!/usr/bin/env node
/**
 * APEX Standard Smart Adapter v1.0
 * Intelligently adapts existing data to APEX Standard
 */

const fs = require('fs');

const RED = '\x1b[31m';
const GREEN = '\x1b[32m';
const YELLOW = '\x1b[33m';
const BLUE = '\x1b[34m';
const CYAN = '\x1b[36m';
const RESET = '\x1b[0m';

let stats = { adapted: 0, skipped: 0, errors: 0 };

function log(type, msg) {
  const prefix = {
    'INFO': `${BLUE}[INFO]${RESET}`,
    'PASS': `${GREEN}[PASS]${RESET}`,
    'FAIL': `${RED}[FAIL]${RESET}`,
    'ADAPT': `${CYAN}[ADAPT]${RESET}`,
    'SUMMARY': `${BLUE}[SUMMARY]${RESET}`
  };
  console.log(`${prefix[type] || '[LOG]'} ${msg}`);
}

// Gene files adapter
function adaptGeneFile(filePath) {
  try {
    const content = fs.readFileSync(filePath, 'utf8');
    const obj = JSON.parse(content);
    
    // Check if it's a genes collection (has genes array) or single gene
    if (obj.genes && Array.isArray(obj.genes)) {
      // Add schema_version to collection
      if (!obj.schema_version) {
        obj.schema_version = '1.0';
        obj.type = 'GeneCollection';
        fs.writeFileSync(filePath, JSON.stringify(obj, null, 2));
        log('ADAPT', `Adapted collection: ${filePath}`);
        stats.adapted++;
      } else {
        log('INFO', `Skipping (compliant): ${filePath}`);
        stats.skipped++;
      }
    } else if (obj.type === 'Gene') {
      if (!obj.schema_version) {
        obj.schema_version = '1.0';
        obj.version = obj.version || 1;
        fs.writeFileSync(filePath, JSON.stringify(obj, null, 2));
        log('ADAPT', `Adapted gene: ${filePath}`);
        stats.adapted++;
      } else {
        log('INFO', `Skipping (compliant): ${filePath}`);
        stats.skipped++;
      }
    } else {
      log('WARN', `Unknown gene format: ${filePath}`);
      stats.skipped++;
    }
  } catch (e) {
    log('FAIL', `Error: ${filePath} - ${e.message}`);
    stats.errors++;
  }
}

// State files adapter
function adaptStateFile(filePath) {
  try {
    const content = fs.readFileSync(filePath, 'utf8');
    const obj = JSON.parse(content);
    
    if (obj.schema_version === '1.0') {
      log('INFO', `Skipping (compliant): ${filePath}`);
      stats.skipped++;
      return;
    }
    
    // Detect state type
    let stateType = 'UnknownState';
    if (obj.cycleCount !== undefined) {
      stateType = 'EvolutionState';
      obj.type = 'EvolutionState';
    } else if (obj.current && obj.current.type === 'PersonalityState') {
      stateType = 'PersonalityState';
      obj.type = 'PersonalityState';
    } else if (obj.last_action && obj.last_action.action_id) {
      stateType = 'MemoryGraphState';
      obj.type = 'MemoryGraphState';
    }
    
    obj.schema_version = '1.0';
    fs.writeFileSync(filePath, JSON.stringify(obj, null, 2));
    log('ADAPT', `Adapted ${stateType}: ${filePath}`);
    stats.adapted++;
    
  } catch (e) {
    log('FAIL', `Error: ${filePath} - ${e.message}`);
    stats.errors++;
  }
}

// Jsonl files adapter
function adaptJsonlFile(filePath) {
  try {
    const content = fs.readFileSync(filePath, 'utf8');
    const lines = content.trim().split('\n');
    let adaptedLines = [];
    let changed = false;
    
    for (const line of lines) {
      if (!line.trim()) continue;
      try {
        const obj = JSON.parse(line);
        
        if (obj.schema_version === '1.0') {
          adaptedLines.push(line);
          continue;
        }
        
        // Add id and ts if missing
        if (!obj.id) {
          const timestamp = obj.ts || obj.timestamp || new Date().toISOString();
          const random = Math.random().toString(36).substring(2, 10);
          obj.id = `evt_${Date.now()}_${random}`;
          changed = true;
        }
        if (!obj.ts) {
          obj.ts = obj.timestamp || new Date().toISOString();
          changed = true;
        }
        
        // Fix MemoryGraphEvent kind
        if (obj.type === 'MemoryGraphEvent' && obj.kind === 'confidence_gene_outcome') {
          obj.kind = 'outcome';
          changed = true;
        }
        
        obj.schema_version = '1.0';
        adaptedLines.push(JSON.stringify(obj));
        if (changed) {
          log('ADAPT', `Adapted line in: ${filePath}`);
        }
      } catch (e) {
        adaptedLines.push(line);
      }
    }
    
    if (changed) {
      fs.writeFileSync(filePath, adaptedLines.join('\n') + '\n');
      log('ADAPT', `Saved: ${filePath}`);
    }
    stats.adapted++;
    
  } catch (e) {
    log('FAIL', `Error: ${filePath} - ${e.message}`);
    stats.errors++;
  }
}

function main() {
  console.log('\n' + '='.repeat(60));
  log('SUMMARY', 'APEX Standard Smart Adapter v1.0');
  console.log('='.repeat(60) + '\n');
  
  // Gene files
  const geneFiles = [
    '/root/.openclaw/workspace/assets/gep/genes.json',
    '/root/.nvm/assets/gep/genes.json',
  ];
  
  log('INFO', 'Adapting Gene files...');
  for (const f of geneFiles) {
    if (fs.existsSync(f)) adaptGeneFile(f);
  }
  
  // State files
  const stateFiles = [
    '/root/.openclaw/workspace/memory/evolution/evolution_state.json',
    '/root/.openclaw/workspace/memory/evolution/memory_graph_state.json',
    '/root/.openclaw/workspace/memory/evolution/personality_state.json',
    '/root/.openclaw/workspace/memory/evolution/question_generator_state.json',
    '/root/.openclaw/workspace/memory/evolution/evolution_solidify_state.json',
    '/root/.openclaw/workspace/patches/healer_state.json',
    '/root/.openclaw/workspace/xuanji_autoresearch_state.json',
  ];
  
  log('INFO', '\nAdapting State files...');
  for (const f of stateFiles) {
    if (fs.existsSync(f)) adaptStateFile(f);
  }
  
  // Jsonl files
  const jsonlFiles = [
    '/root/.openclaw/workspace/assets/gep/candidates.jsonl',
    '/root/.openclaw/workspace/assets/gep/events.jsonl',
    '/root/.openclaw/workspace/memory/.dreams/events.jsonl',
    '/root/.openclaw/workspace/memory/evolution/asset_call_log.jsonl',
    '/root/.openclaw/workspace/memory/evolution/memory_graph.jsonl',
    '/root/.openclaw/workspace/memory/evolution/reflection_log.jsonl',
    '/root/.nvm/assets/gep/candidates.jsonl',
    '/root/.nvm/assets/gep/events.jsonl',
  ];
  
  log('INFO', '\nAdapting Jsonl files...');
  for (const f of jsonlFiles) {
    if (fs.existsSync(f)) adaptJsonlFile(f);
  }
  
  console.log('\n' + '='.repeat(60));
  log('SUMMARY', `Adaptation Complete`);
  console.log('='.repeat(60));
  log('SUMMARY', `Adapted: ${CYAN}${stats.adapted}${RESET}`);
  log('SUMMARY', `Skipped: ${YELLOW}${stats.skipped}${RESET}`);
  log('SUMMARY', `Errors: ${stats.errors > 0 ? RED : GREEN}${stats.errors}${RESET}`);
  console.log('='.repeat(60) + '\n');
  
  process.exit(stats.errors > 0 ? 1 : 0);
}

main();
