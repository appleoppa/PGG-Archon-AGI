#!/usr/bin/env node
/**
 * APEX Standard Migration Script v1.0
 * Migrates existing data files to APEX Unified Data Standard
 */

const fs = require('fs');
const path = require('path');

const WORKSPACE_DIR = '/root/.openclaw/workspace';
const NVM_DIR = '/root/.nvm';

const RED = '\x1b[31m';
const GREEN = '\x1b[32m';
const YELLOW = '\x1b[33m';
const BLUE = '\x1b[34m';
const CYAN = '\x1b[36m';
const RESET = '\x1b[0m';

let stats = { migrated: 0, skipped: 0, errors: 0 };

function log(type, msg) {
  const prefix = {
    'INFO': `${BLUE}[INFO]${RESET}`,
    'PASS': `${GREEN}[PASS]${RESET}`,
    'FAIL': `${RED}[FAIL]${RESET}`,
    'WARN': `${YELLOW}[WARN]${RESET}`,
    'MIGRATE': `${CYAN}[MIGRATE]${RESET}`,
    'SUMMARY': `${BLUE}[SUMMARY]${RESET}`
  };
  console.log(`${prefix[type] || '[LOG]'} ${msg}`);
}

function addSchemaVersion(obj) {
  if (!obj) return obj;
  return {
    ...obj,
    schema_version: '1.0'
  };
}

function migrateJsonFile(filePath) {
  try {
    const content = fs.readFileSync(filePath, 'utf8');
    const obj = JSON.parse(content);
    
    // Skip if already has schema_version
    if (obj.schema_version === '1.0') {
      log('INFO', `Skipping (already compliant): ${filePath}`);
      stats.skipped++;
      return;
    }
    
    // Add schema_version
    const migrated = addSchemaVersion(obj);
    
    // Write back
    fs.writeFileSync(filePath, JSON.stringify(migrated, null, 2));
    log('MIGRATE', `Migrated: ${filePath}`);
    stats.migrated++;
    
  } catch (e) {
    log('FAIL', `Error migrating ${filePath}: ${e.message}`);
    stats.errors++;
  }
}

function migrateJsonlFile(filePath) {
  try {
    const content = fs.readFileSync(filePath, 'utf8');
    const lines = content.trim().split('\n');
    let migratedLines = [];
    let changed = false;
    
    for (const line of lines) {
      if (!line.trim()) continue;
      try {
        const obj = JSON.parse(line);
        if (obj.schema_version !== '1.0') {
          const migrated = addSchemaVersion(obj);
          migratedLines.push(JSON.stringify(migrated));
          changed = true;
        } else {
          migratedLines.push(line);
        }
      } catch (e) {
        migratedLines.push(line);
      }
    }
    
    if (changed) {
      fs.writeFileSync(filePath, migratedLines.join('\n') + '\n');
      log('MIGRATE', `Migrated: ${filePath}`);
      stats.migrated++;
    } else {
      log('INFO', `Skipping (already compliant): ${filePath}`);
      stats.skipped++;
    }
    
  } catch (e) {
    log('FAIL', `Error migrating ${filePath}: ${e.message}`);
    stats.errors++;
  }
}

function processDirectory(dir, extensions) {
  function walk(directory) {
    try {
      const files = fs.readdirSync(directory);
      for (const file of files) {
        const fullPath = path.join(directory, file);
        try {
          const stat = fs.statSync(fullPath);
          if (stat.isDirectory()) {
            if (file !== 'node_modules' && file !== '.git' && file !== 'standard') {
              walk(fullPath);
            }
          } else if (stat.isFile()) {
            for (const ext of extensions) {
              if (fullPath.endsWith(ext)) {
                if (ext === '.jsonl') {
                  migrateJsonlFile(fullPath);
                } else if (ext === '.json') {
                  migrateJsonFile(fullPath);
                }
                break;
              }
            }
          }
        } catch (e) {
          log('WARN', `Cannot access ${fullPath}: ${e.message}`);
        }
      }
    } catch (e) {
      log('WARN', `Cannot read directory ${directory}: ${e.message}`);
    }
  }
  
  walk(dir);
}

function main() {
  console.log('\n' + '='.repeat(60));
  log('SUMMARY', 'APEX Standard Migration Script v1.0');
  console.log('='.repeat(60) + '\n');
  
  const filesToMigrate = [
    // Gene files
    '/root/.openclaw/workspace/assets/gep/genes.json',
    '/root/.nvm/assets/gep/genes.json',
    
    // State files
    '/root/.openclaw/workspace/memory/evolution/evolution_state.json',
    '/root/.openclaw/workspace/memory/evolution/memory_graph_state.json',
    '/root/.openclaw/workspace/memory/evolution/personality_state.json',
    '/root/.openclaw/workspace/memory/evolution/question_generator_state.json',
    '/root/.openclaw/workspace/memory/evolution/evolution_solidify_state.json',
    
    // Jsonl files
    '/root/.openclaw/workspace/assets/gep/candidates.jsonl',
    '/root/.openclaw/workspace/assets/gep/events.jsonl',
    '/root/.openclaw/workspace/memory/.dreams/events.jsonl',
    '/root/.openclaw/workspace/memory/evolution/asset_call_log.jsonl',
    '/root/.openclaw/workspace/memory/evolution/memory_graph.jsonl',
    '/root/.openclaw/workspace/memory/evolution/reflection_log.jsonl',
    '/root/.nvm/assets/gep/candidates.jsonl',
    '/root/.nvm/assets/gep/events.jsonl',
  ];
  
  log('INFO', 'Migrating fixed file list...\n');
  
  for (const file of filesToMigrate) {
    if (fs.existsSync(file)) {
      if (file.endsWith('.jsonl')) {
        migrateJsonlFile(file);
      } else {
        migrateJsonFile(file);
      }
    } else {
      log('INFO', `File not found (skipping): ${file}`);
      stats.skipped++;
    }
  }
  
  console.log('\n' + '='.repeat(60));
  log('SUMMARY', `Migration Complete`);
  console.log('='.repeat(60));
  log('SUMMARY', `Migrated: ${GREEN}${stats.migrated}${RESET}`);
  log('SUMMARY', `Skipped: ${YELLOW}${stats.skipped}${RESET}`);
  log('SUMMARY', `Errors: ${stats.errors > 0 ? RED : GREEN}${stats.errors}${RESET}`);
  console.log('='.repeat(60) + '\n');
  
  process.exit(stats.errors > 0 ? 1 : 0);
}

main();
