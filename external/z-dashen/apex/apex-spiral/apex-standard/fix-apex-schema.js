#!/usr/bin/env node
/**
 * APEX Standard Fix Script v1.0
 * Fixes schema_version placement and adds missing type fields
 */

const fs = require('fs');

const RED = '\x1b[31m';
const GREEN = '\x1b[32m';
const YELLOW = '\x1b[33m';
const BLUE = '\x1b[34m';
const CYAN = '\x1b[36m';
const RESET = '\x1b[0m';

let stats = { fixed: 0, skipped: 0, errors: 0 };

function log(type, msg) {
  const prefix = {
    'INFO': `${BLUE}[INFO]${RESET}`,
    'PASS': `${GREEN}[PASS]${RESET}`,
    'FAIL': `${RED}[FAIL]${RESET}`,
    'FIX': `${CYAN}[FIX]${RESET}`,
    'SUMMARY': `${BLUE}[SUMMARY]${RESET}`
  };
  console.log(`${prefix[type] || '[LOG]'} ${msg}`);
}

// Fix state files - move type to root level
function fixStateFile(filePath) {
  try {
    const content = fs.readFileSync(filePath, 'utf8');
    const obj = JSON.parse(content);
    
    // Add type field at root level based on content
    if (!obj.type) {
      if (obj.cycleCount !== undefined) {
        obj.type = 'EvolutionState';
      } else if (obj.last_action !== undefined) {
        obj.type = 'MemoryGraphState';
      } else if (obj.current !== undefined) {
        obj.type = 'PersonalityState';
      }
    }
    
    fs.writeFileSync(filePath, JSON.stringify(obj, null, 2));
    log('FIX', `Fixed: ${filePath}`);
    stats.fixed++;
    
  } catch (e) {
    log('FAIL', `Error fixing ${filePath}: ${e.message}`);
    stats.errors++;
  }
}

// Fix jsonl files - ensure schema_version at object root
function fixJsonlFile(filePath) {
  try {
    const content = fs.readFileSync(filePath, 'utf8');
    const lines = content.trim().split('\n');
    let fixedLines = [];
    let changed = false;
    
    for (const line of lines) {
      if (!line.trim()) continue;
      try {
        const obj = JSON.parse(line);
        
        // Move schema_version to root if it's at the end
        const objCopy = { ...obj };
        if (obj.schema_version !== undefined) {
          delete objCopy.schema_version;
        }
        
        // Ensure id and ts exist
        if (!obj.id) {
          objCopy.id = `evt_${Date.now()}_${Math.random().toString(36).substring(2,8)}`;
          changed = true;
        }
        if (!obj.ts) {
          objCopy.ts = obj.timestamp || new Date().toISOString();
          changed = true;
        }
        
        // Add schema_version at root
        objCopy.schema_version = '1.0';
        
        // Fix MemoryGraphEvent kind
        if (obj.kind === 'confidence_gene_outcome') {
          objCopy.kind = 'outcome';
          changed = true;
        }
        
        fixedLines.push(JSON.stringify(objCopy));
        if (changed) stats.fixed++;
        
      } catch (e) {
        fixedLines.push(line);
      }
    }
    
    if (changed) {
      fs.writeFileSync(filePath, fixedLines.join('\n') + '\n');
      log('FIX', `Saved: ${filePath}`);
    } else {
      stats.skipped++;
    }
    
  } catch (e) {
    log('FAIL', `Error fixing ${filePath}: ${e.message}`);
    stats.errors++;
  }
}

function main() {
  console.log('\n' + '='.repeat(60));
  log('SUMMARY', 'APEX Standard Fix Script v1.0');
  console.log('='.repeat(60) + '\n');
  
  // Fix state files
  const stateFiles = [
    '/root/.openclaw/workspace/memory/evolution/evolution_state.json',
    '/root/.openclaw/workspace/memory/evolution/memory_graph_state.json',
    '/root/.openclaw/workspace/memory/evolution/personality_state.json',
    '/root/.openclaw/workspace/memory/evolution/question_generator_state.json',
    '/root/.openclaw/workspace/memory/evolution/evolution_solidify_state.json',
  ];
  
  log('INFO', 'Fixing State files...');
  for (const f of stateFiles) {
    if (fs.existsSync(f)) fixStateFile(f);
  }
  
  // Fix jsonl files
  const jsonlFiles = [
    '/root/.openclaw/workspace/assets/gep/candidates.jsonl',
    '/root/.openclaw/workspace/assets/gep/events.jsonl',
    '/root/.openclaw/workspace/memory/.dreams/events.jsonl',
    '/root/.openclaw/workspace/memory/evolution/asset_call_log.jsonl',
    '/root/.openclaw/workspace/memory/evolution/memory_graph.jsonl',
    '/root/.openclaw/workspace/memory/evolution/reflection_log.jsonl',
  ];
  
  log('INFO', '\nFixing Jsonl files...');
  for (const f of jsonlFiles) {
    if (fs.existsSync(f)) fixJsonlFile(f);
  }
  
  console.log('\n' + '='.repeat(60));
  log('SUMMARY', `Fix Complete`);
  console.log('='.repeat(60));
  log('SUMMARY', `Fixed: ${CYAN}${stats.fixed}${RESET}`);
  log('SUMMARY', `Skipped: ${YELLOW}${stats.skipped}${RESET}`);
  log('SUMMARY', `Errors: ${stats.errors > 0 ? RED : GREEN}${stats.errors}${RESET}`);
  console.log('='.repeat(60) + '\n');
  
  process.exit(stats.errors > 0 ? 1 : 0);
}

main();
