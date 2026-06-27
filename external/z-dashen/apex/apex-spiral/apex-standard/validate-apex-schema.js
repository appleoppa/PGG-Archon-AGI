#!/usr/bin/env node
/**
 * APEX Unified Data Standard Validator v1.0 (Updated)
 * Validates all APEX data files against standard schemas with extensible types
 */

const fs = require('fs');
const path = require('path');

const STANDARD_DIR = path.join(__dirname);
const WORKSPACE_DIR = '/root/.openclaw/workspace';
const NVM_DIR = '/root/.nvm';

const RED = '\x1b[31m';
const GREEN = '\x1b[32m';
const YELLOW = '\x1b[33m';
const BLUE = '\x1b[34m';
const RESET = '\x1b[0m';

let stats = { passed: 0, failed: 0, warnings: 0 };

function log(type, msg) {
  const prefix = {
    'INFO': `${BLUE}[INFO]${RESET}`,
    'PASS': `${GREEN}[PASS]${RESET}`,
    'FAIL': `${RED}[FAIL]${RESET}`,
    'WARN': `${YELLOW}[WARN]${RESET}`,
    'SUMMARY': `${BLUE}[SUMMARY]${RESET}`
  };
  console.log(`${prefix[type] || '[LOG]'} ${msg}`);
}

function validateSchemaVersion(obj) {
  if (!obj || typeof obj !== 'object') return false;
  if (obj.schema_version !== '1.0' && !obj.schemaVersion) {
    return { valid: false, reason: 'Missing schema_version field' };
  }
  return { valid: true };
}

function validateGeneSchema(obj) {
  const result = validateSchemaVersion(obj);
  if (!result.valid) return result;
  
  // Handle GeneCollection (has genes array)
  if (obj.genes && Array.isArray(obj.genes)) {
    if (!obj.type) {
      return { valid: false, reason: 'GeneCollection missing type field' };
    }
    return { valid: true };
  }
  
  // Handle single Gene
  if (obj.type === 'Gene') {
    if (!obj.id || !obj.id.startsWith('gene_')) {
      return { valid: false, reason: 'id must start with "gene_"' };
    }
    if (!obj.category || !['repair', 'optimize', 'innovate', 'orchestrate', 'evolve'].includes(obj.category)) {
      return { valid: false, reason: 'Invalid category' };
    }
    return { valid: true };
  }
  
  return { valid: true }; // Allow other types
}

function validateEventSchema(obj) {
  const result = validateSchemaVersion(obj);
  if (!result.valid) return result;
  
  if (!obj.id || !obj.ts) {
    return { valid: false, reason: 'Missing id or ts field' };
  }
  
  // Check for MemoryGraphEvent
  if (obj.type === 'MemoryGraphEvent') {
    if (!obj.kind) {
      return { valid: false, reason: 'MemoryGraphEvent requires kind field' };
    }
    const validKinds = ['signal', 'hypothesis', 'attempt', 'outcome', 'confidence_edge', 'observation'];
    if (!validKinds.includes(obj.kind)) {
      return { valid: false, reason: `Invalid kind: ${obj.kind}` };
    }
  }
  
  return { valid: true };
}

function validateStateSchema(obj) {
  const result = validateSchemaVersion(obj);
  if (!result.valid) return result;
  
  if (!obj.type) {
    return { valid: false, reason: 'Missing type field' };
  }
  
  // Core APEX state types
  const validTypes = ['EvolutionState', 'PersonalityState', 'MemoryGraphState'];
  
  // Extended types (external systems)
  const extendedTypes = [
    'EvolutionSolidifyState', 'QuestionGeneratorState', 'HealerState',
    'AutoresearchState', 'GeneCollection', 'ApexCapsule', 'ApexGene'
  ];
  
  const allValidTypes = [...validTypes, ...extendedTypes];
  
  if (!allValidTypes.includes(obj.type)) {
    return { valid: false, reason: `Invalid state type: ${obj.type}` };
  }
  
  return { valid: true };
}

function validateFile(filePath, validator) {
  try {
    const content = fs.readFileSync(filePath, 'utf8');
    
    // Handle jsonl files
    if (filePath.endsWith('.jsonl')) {
      const lines = content.trim().split('\n');
      let lineNum = 0;
      let hasFailure = false;
      for (const line of lines) {
        lineNum++;
        if (!line.trim()) continue;
        try {
          const obj = JSON.parse(line);
          const result = validator(obj);
          if (!result.valid) {
            log('FAIL', `${filePath}:${lineNum} - ${result.reason}`);
            hasFailure = true;
          }
        } catch (e) {
          log('FAIL', `${filePath}:${lineNum} - JSON parse error: ${e.message}`);
          hasFailure = true;
        }
      }
      if (!hasFailure) {
        log('PASS', filePath);
        stats.passed++;
      }
      return;
    } else {
      // Handle JSON files
      const obj = JSON.parse(content);
      const result = validator(obj);
      if (!result.valid) {
        log('FAIL', `${filePath} - ${result.reason}`);
        stats.failed++;
        return;
      }
    }
    
    log('PASS', filePath);
    stats.passed++;
    
  } catch (e) {
    log('FAIL', `${filePath} - Error: ${e.message}`);
    stats.failed++;
  }
}

function scanDirectory(dir, patterns, validator) {
  log('INFO', `Scanning ${dir}...`);
  
  function walk(directory) {
    try {
      const files = fs.readdirSync(directory);
      for (const file of files) {
        const fullPath = path.join(directory, file);
        try {
          const stat = fs.statSync(fullPath);
          
          if (stat.isDirectory()) {
            // Skip node_modules and .git
            if (file !== 'node_modules' && file !== '.git') {
              walk(fullPath);
            }
          } else if (stat.isFile()) {
            for (const pattern of patterns) {
              if (file.match(pattern)) {
                validateFile(fullPath, validator);
                break;
              }
            }
          }
        } catch (e) {
          // Skip inaccessible files
        }
      }
    } catch (e) {
      log('WARN', `Cannot access ${directory}: ${e.message}`);
      stats.warnings++;
    }
  }
  
  walk(dir);
}

function main() {
  console.log('\n' + '='.repeat(60));
  log('SUMMARY', 'APEX Unified Data Standard Validator v1.0');
  console.log('='.repeat(60) + '\n');
  
  log('INFO', 'Validating Gene files...');
  scanDirectory(WORKSPACE_DIR, [/genes\.json$/, /gene.*\.json$/], validateGeneSchema);
  scanDirectory(NVM_DIR, [/genes\.json$/, /gene.*\.json$/], validateGeneSchema);
  
  log('INFO', '\nValidating Event files...');
  scanDirectory(WORKSPACE_DIR, [/\.jsonl$/], validateEventSchema);
  scanDirectory(NVM_DIR, [/\.jsonl$/], validateEventSchema);
  
  log('INFO', '\nValidating State files...');
  scanDirectory(WORKSPACE_DIR, [/_state\.json$/, /evolution.*\.json$/, /patches\/.*\.json$/], validateStateSchema);
  scanDirectory(NVM_DIR, [/_state\.json$/, /evolution.*\.json$/], validateStateSchema);
  
  console.log('\n' + '='.repeat(60));
  log('SUMMARY', `Validation Complete`);
  console.log('='.repeat(60));
  log('SUMMARY', `Passed: ${GREEN}${stats.passed}${RESET}`);
  log('SUMMARY', `Failed: ${stats.failed > 0 ? RED : GREEN}${stats.failed}${RESET}`);
  log('SUMMARY', `Warnings: ${stats.warnings > 0 ? YELLOW : GREEN}${stats.warnings}${RESET}`);
  console.log('='.repeat(60) + '\n');
  
  process.exit(stats.failed > 0 ? 1 : 0);
}

main();
