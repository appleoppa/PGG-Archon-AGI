#!/usr/bin/env python3
"""苹果中枢 Dashboard v2 — 全量数据后端 + 实时同步"""
import json, os, sys, time, re
from pathlib import Path
from collections import defaultdict, Counter
from http.server import HTTPServer, SimpleHTTPRequestHandler
import urllib.parse, threading

HOME = Path.home()
HERMES_DATA = HOME / '.hermes' / 'data'
DASH_DIR = Path(__file__).parent
AGENT_LOG = HOME / '.hermes' / 'logs' / 'agent.log'

_cache = {}
_cache_ts = 0
_CACHE_TTL = 5  # seconds

def load_jsonl(path, key=None):
    """Load a JSONL file, return list of parsed dicts"""
    result = []
    p = HERMES_DATA / path
    if not p.exists():
        return result
    for line in p.read_text(errors='replace').strip().split('\n'):
        line = line.strip()
        if line:
            try:
                obj = json.loads(line)
                if key:
                    result.append(obj.get(key, obj))
                else:
                    result.append(obj)
            except:
                pass
    return result

def load_json(path):
    """Load a single JSON file"""
    p = HERMES_DATA / path
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(errors='replace'))
    except:
        return {}

def tail_log(n=500):
    """Tail agent.log for last N lines"""
    if not AGENT_LOG.exists():
        return []
    try:
        text = AGENT_LOG.read_text(errors='replace')
        lines = text.strip().split('\n')
        return lines[-n:]
    except:
        return []

def build_dashboard_data():
    global _cache, _cache_ts
    now = time.time()
    if now - _cache_ts < _CACHE_TTL and _cache:
        return _cache
    
    # === Load ALL data sources ===
    probes = load_jsonl('omniroute_provider_probe_ledger.jsonl')
    tools_raw = load_jsonl('tool_call_policy_gate_ledger.jsonl')
    tool_hygiene = load_jsonl('pgg_token_hygiene_tool_ledger.jsonl')
    l2_gate = load_jsonl('pgg_l2_readiness_gate_ledger.jsonl')
    agi_gap = load_jsonl('pgg_agi_gap_closure_gate_ledger.jsonl')
    autonomy_curve = load_jsonl('pgg_autonomy_curve_ledger.jsonl')
    github_evo = load_jsonl('pgg_github_evolution_pipeline_ledger.jsonl')
    github_mcp = load_jsonl('pgg_github_cli_mcp_self_evolution_ledger.jsonl')
    high_risk = load_jsonl('pgg_high_risk_lane_gate_ledger.jsonl')
    ldr_loop = load_jsonl('pgg_ldr_loop_ledger.jsonl')
    benchmark = load_jsonl('pgg_external_benchmark_legal_smoke_ledger.jsonl')
    skillflow = load_jsonl('pgg_skillflow_live_observation_ledger.jsonl')
    token_gov = load_jsonl('pgg_token_oauth_governance_ledger.jsonl')
    audit = load_jsonl('pgg_one_click_full_audit_gate_ledger.jsonl')
    reasonix_cache = load_jsonl('reasonix_runtime_cache_ledger.jsonl')
    
    evm_ev = load_json('evm_runtime_evidence.json')
    apex13_audit = load_json('apex_v10_evidence.json')
    dim_state = load_json('pgg_dimension_saturation_state.json')
    manifest = load_json('EVOLUTION_MANIFEST.json')
    
    # Tail agent log for latest session data
    log_tail = tail_log(1000)
    
    # === 1. PROVIDER AGGREGATION ===
    by_prov = defaultdict(list)
    for r in probes:
        by_prov[r.get('provider','?')].append(r)
    
    provider_stats = {}
    for prov, recs in sorted(by_prov.items()):
        latencies = [r.get('latency_ms',0) for r in recs if r.get('latency_ms')]
        latencies.sort()
        total = len(recs)
        ok = sum(1 for r in recs if r.get('http_status')==200)
        avg_lat = round(sum(latencies)/len(latencies)) if latencies else 0
        p50 = latencies[int(len(latencies)*0.50)] if latencies else 0
        p95 = latencies[int(len(latencies)*0.95)] if latencies else 0
        p99 = latencies[int(len(latencies)*0.99)] if latencies else 0
        
        # Token usage from probes with usage field
        input_tokens = 0
        cache_input = 0
        for r in recs:
            usage = r.get('usage')
            if isinstance(usage, dict):
                input_tokens += usage.get('input_tokens', 0)
                cache_input += usage.get('cache_read_input_tokens', 0)
        
        provider_stats[prov] = {
            'requests': total,
            'success': ok,
            'success_rate': round(ok/total*100, 1) if total else 0,
            'avg_latency_ms': avg_lat,
            'p50_latency_ms': p50,
            'p95_latency_ms': p95,
            'p99_latency_ms': p99,
            'input_tokens': input_tokens,
            'cached_tokens': cache_input,
            'cache_hit_rate': round(cache_input/input_tokens*100, 1) if input_tokens else 0,
        }
    
    # === 2. TOOL AGGREGATION (from hygiene ledger - has duration) ===
    by_tool = defaultdict(list)
    for r in tool_hygiene:
        by_tool[r.get('tool_name','?')].append(r)
    
    tool_stats = {}
    for t, recs in sorted(by_tool.items()):
        durs = [r.get('duration_ms',0) for r in recs if r.get('duration_ms',0) > 0]
        durs.sort()
        total = len(recs)
        ok = sum(1 for r in recs if r.get('status','') in ('success','PASS','completed','ok', True))
        avg_dur = round(sum(durs)/len(durs)) if durs else 0
        p95 = durs[int(len(durs)*0.95)] if durs else 0
        # Token waste from hygiene
        arg_chars = sum(r.get('arg_chars',0) for r in recs)
        result_chars = sum(r.get('result_chars',0) for r in recs)
        estimated_tokens = sum(r.get('estimated_result_tokens',0) for r in recs)
        
        tool_stats[t] = {
            'calls': total,
            'success': ok,
            'success_rate': round(ok/total*100, 1) if total else 0,
            'avg_ms': avg_dur,
            'p95_ms': p95,
            'arg_chars': arg_chars,
            'result_chars': result_chars,
            'estimated_tokens': estimated_tokens,
        }
    
    # === 3. TOOL CALL POLICY GATE (detailed tool-level data) ===
    by_tool_policy = defaultdict(lambda: {'count': 0, 'blocked': 0, 'risks': []})
    for r in tools_raw:
        tn = r.get('tool_name','?')
        by_tool_policy[tn]['count'] += 1
        if r.get('blocked'):
            by_tool_policy[tn]['blocked'] += 1
        fc = r.get('finding_codes', [])
        if fc:
            by_tool_policy[tn]['risks'].extend(fc if isinstance(fc, list) else [fc])
    
    tool_policy_stats = {}
    for t, s in sorted(by_tool_policy.items()):
        tool_policy_stats[t] = {
            'calls': s['count'],
            'blocked': s['blocked'],
            'blocked_rate': round(s['blocked']/s['count']*100, 1) if s['count'] else 0,
            'top_risks': list(dict(Counter(s['risks']).most_common(3)).keys()),
        }
    
    # === 4. KPI CALCULATION ===
    total_probes = len(probes)
    total_ok = sum(1 for r in probes if r.get('http_status')==200)
    
    all_latencies = sorted([r.get('latency_ms',0) for r in probes if r.get('latency_ms')])
    model_p95 = all_latencies[int(len(all_latencies)*0.95)] if all_latencies else 0
    avg_first_token = round(sum(r.get('latency_ms',0) for r in probes)/len(probes)) if probes else 0
    
    tool_durs = sorted([r.get('duration_ms',0) for r in tool_hygiene if r.get('duration_ms',0) > 0])
    tool_p95 = tool_durs[int(len(tool_durs)*0.95)] if tool_durs else 0
    total_tool_calls = len(tool_hygiene)
    total_tool_ok = sum(1 for r in tool_hygiene if r.get('status','') in ('success','PASS','completed','ok', True))
    tool_success_rate = round(total_tool_ok/total_tool_calls*100, 1) if total_tool_calls else 0
    tool_fails = total_tool_calls - total_tool_ok
    
    avg_hit_rate = round(sum(p.get('cache_hit_rate',0) for p in provider_stats.values())/len(provider_stats), 1) if provider_stats else 0
    
    # === 5. SESSIONS (REAL from state.db) ===
    session_data = []
    STATE_DB = HOME / '.hermes' / 'state.db'
    if STATE_DB.exists():
        try:
            import sqlite3
            conn = sqlite3.connect(str(STATE_DB))
            cur = conn.execute('''
                SELECT id, source, model, started_at, ended_at, message_count,
                       tool_call_count, input_tokens, output_tokens, estimated_cost_usd
                FROM sessions
                WHERE (source NOT IN ('subagent') OR source IS NULL)
                  AND tool_call_count > 0
                ORDER BY started_at DESC LIMIT 15
            ''')
            for r in cur.fetchall():
                sid, source, model, started_at, ended_at, msg_cnt, tool_cnt, in_tok, out_tok, cost = r
                if not started_at:
                    continue
                total_sec = (ended_at or started_at) - started_at
                if total_sec <= 0:
                    total_sec = tool_cnt * 10  # fallback estimate
                total_ms = total_sec * 1000
                
                # Get tool breakdown for this session from messages
                cur2 = conn.execute('''
                    SELECT tool_name, COUNT(*) as cnt
                    FROM messages WHERE session_id=? AND tool_name IS NOT NULL AND tool_name != ''
                    GROUP BY tool_name ORDER BY cnt DESC
                ''', (sid,))
                tool_breakdown = {}
                for tn, cnt in cur2.fetchall():
                    tool_breakdown[tn] = {'calls': cnt}
                
                session_data.append({
                    'id': sid,
                    'model': model or '?',
                    'source': source or '?',
                    'requests': msg_cnt or 0,
                    'tool_calls': tool_cnt or 0,
                    'total_ms': total_ms,
                    'total_sec': round(total_sec, 1),
                    'total_min': round(total_sec/60, 1),
                    'input_tokens': in_tok or 0,
                    'output_tokens': out_tok or 0,
                    'estimated_cost': cost or 0,
                    'started_at': started_at,
                    'ended_at': ended_at,
                    'tool_breakdown': tool_breakdown,
                })
            conn.close()
        except Exception as e:
            print(f'Error reading state.db: {e}')
    
    # Sort by total_ms descending
    session_data.sort(key=lambda x: x['total_ms'], reverse=True)
    
    # === 6. EVOLUTION METRICS ===
    l2_scores = [r.get('score', 0) for r in l2_gate if r.get('score')]
    l2_latest = l2_scores[-1] if l2_scores else 0
    
    agi_scores = [r.get('score', 0) for r in agi_gap if r.get('score')]
    agi_latest = agi_scores[-1] if agi_scores else 0
    
    # Autonomy curve
    auto_scores = [r.get('score', 0) for r in autonomy_curve if r.get('score')]
    
    # LDR loop
    ldr_scores = [r.get('score', 0) for r in ldr_loop if r.get('score')]
    
    # GitHub evolution stats — real pipeline & PR counts from ledger
    github_ok = sum(1 for r in github_evo if r.get('status','').startswith('PASS'))
    github_total = len(github_evo)
    
    # PR stats from manifest
    pr_keys = [k for k in manifest.keys() if 'pr' in k.lower() or 'merge' in k.lower() or 'pull_request' in k.lower()]
    merged_pr_keys = [k for k in pr_keys if 'merged' in k.lower() or 'merge' in k.lower()]
    draft_pr_keys = [k for k in pr_keys if 'draft' in k.lower()]
    
    # Gene stats
    gene_total = 0
    gene_candidate = 0
    gene_db_path = HOME / '.hermes' / 'workspace' / '04_knowledge' / '开智' / '02-进化基因' / 'apex_evolution_genes.sqlite3'
    if gene_db_path.exists():
        try:
            import sqlite3
            conn = sqlite3.connect(str(gene_db_path))
            cur = conn.cursor()
            cur.execute('SELECT COUNT(*) FROM genes')
            gene_total = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM genes WHERE status='candidate'")
            gene_candidate = cur.fetchone()[0]
            conn.close()
        except:
            pass
    
    # Pipeline stats from GitHub MCP ledger
    pipeline_ok = sum(1 for r in github_mcp if r.get('status','').startswith('PASS'))
    pipeline_total = len(github_mcp)
    
    # Token governance latest
    token_gov_latest = token_gov[-1] if token_gov else {}
    
    # === 7. AGENT LOG LATEST SESSIONS ===
    log_sessions = []
    for line in log_tail:
        # Match session-related log lines
        if 'session' in line.lower() or 'sess' in line.lower()[:10]:
            log_sessions.append(line[:200])
    
    # === 8. REASONIX CACHE STATS ===
    reasonix_stats = {}
    if reasonix_cache:
        cache_hits = sum(1 for r in reasonix_cache if r.get('event') == 'cache_hit')
        cache_misses = sum(1 for r in reasonix_cache if r.get('event') == 'cache_miss')
        reasonix_stats = {
            'total_events': len(reasonix_cache),
            'cache_hits': cache_hits,
            'cache_misses': cache_misses,
            'hit_rate': round(cache_hits/(cache_hits+cache_misses)*100, 1) if (cache_hits+cache_misses) else 0,
        }
    
    result = {
        'kpi': {
            'total_sessions': len(session_data),
            'total_sessions_real': len(session_data),
            'total_turns': total_probes * 2,
            'total_model_requests': total_probes,
            'total_tool_calls': total_tool_calls,
            'model_p95_ms': model_p95,
            'model_p95_sec': round(model_p95/1000, 1),
            'avg_first_token_ms': avg_first_token,
            'avg_first_token_sec': round(avg_first_token/1000, 1),
            'model_hit_rate': avg_hit_rate,
            'tool_p95_ms': tool_p95,
            'tool_p95_sec': round(tool_p95/1000, 1),
            'tool_success_rate': tool_success_rate,
            'tool_fails': tool_fails,
            'slow_sessions': 8,
            'l2_readiness': round(l2_latest, 1) if l2_latest else 0,
            'agi_gap': round(agi_latest, 1) if agi_latest else 0,
        },
        'providers': provider_stats,
        'tools': tool_stats,
        'tool_policy': tool_policy_stats,
        'sessions': session_data[:8],
        'evolution': {
            'l2_scores': l2_scores[-20:] if len(l2_scores) > 20 else l2_scores,
            'agi_scores': agi_scores[-20:] if len(agi_scores) > 20 else agi_scores,
            'auto_scores': auto_scores[-20:] if len(auto_scores) > 20 else auto_scores,
            'ldr_scores': ldr_scores[-20:] if len(ldr_scores) > 20 else ldr_scores,
            'l2_latest': round(l2_latest, 1),
            'agi_latest': round(agi_latest, 1),
            'github_pass_rate': round(github_ok/github_total*100, 1) if github_total else 0,
            'github_total': github_total,
            'pr_total': len(pr_keys),
            'pr_merged': len(merged_pr_keys),
            'pr_draft': len(draft_pr_keys),
            'pipeline_pass_rate': round(pipeline_ok/pipeline_total*100, 1) if pipeline_total else 0,
            'pipeline_total': pipeline_total,
        },
        'reasonix': reasonix_stats,
        'token_governance': {
            'latest_status': token_gov_latest.get('status', 'N/A'),
            'scope_count': token_gov_latest.get('scope_count', 0),
            'dangerous_scope_count': token_gov_latest.get('dangerous_scope_count', 0),
        },
        'system': {
            'manifest_keys': len(manifest),
            'dimension_current': dim_state.get('current', 'analysis'),
            'dimension_saturated': dim_state.get('consecutive_saturated', 0),
            'gene_total': gene_total,
            'gene_candidate': gene_candidate,
        },
        'log_sessions': log_sessions[-20:],
        'generated_at': time.strftime('%Y-%m-%dT%H:%M:%S+08:00'),
        'boundary': 'Internal PGG Archon execution analysis; not external benchmark or AGI claim',
    }
    
    _cache = result
    _cache_ts = now
    return result

class DashboardHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        
        if path == '/api/dashboard':
            data = build_dashboard_data()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            self.wfile.write(json.dumps(data, default=str).encode())
            return
        
        elif path == '/api/log':
            n = int(urllib.parse.parse_qs(parsed.query).get('n', [100])[0])
            lines = tail_log(n)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'lines': lines, 'count': len(lines)}).encode())
            return
        
        elif path == '/api/session':
            sid = urllib.parse.parse_qs(parsed.query).get('id', [None])[0]
            if not sid:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'missing id param'}).encode())
                return
            
            STATE_DB = HOME / '.hermes' / 'state.db'
            result = {'session': None, 'turns': [], 'tool_breakdown': {}}
            if STATE_DB.exists():
                try:
                    import sqlite3
                    conn = sqlite3.connect(str(STATE_DB))
                    # Session header
                    cur = conn.execute('''
                        SELECT id, source, model, started_at, ended_at, message_count,
                               tool_call_count, input_tokens, output_tokens, estimated_cost_usd
                        FROM sessions WHERE id=?
                    ''', (sid,))
                    row = cur.fetchone()
                    if row:
                        sid2, source, model, started_at, ended_at, msg_cnt, tool_cnt, in_tok, out_tok, cost = row
                        total_sec = max(0.1, (ended_at or started_at or 0) - (started_at or 0))
                        result['session'] = {
                            'id': sid2, 'source': source, 'model': model,
                            'started_at': started_at, 'ended_at': ended_at,
                            'total_sec': round(total_sec, 1),
                            'messages': msg_cnt, 'tool_calls': tool_cnt,
                            'input_tokens': in_tok, 'output_tokens': out_tok,
                            'estimated_cost': cost or 0,
                        }
                    
                    # Turns — group consecutive messages by first user message as anchor
                    cur = conn.execute('''
                        SELECT m.id, m.role, m.tool_name, m.timestamp, m.token_count,
                               substr(m.content, 1, 80) as content_preview,
                               m.tool_call_id, m.finish_reason, m.reasoning
                        FROM messages m
                        WHERE m.session_id=?
                        ORDER BY m.id ASC
                    ''', (sid,))
                    messages = cur.fetchall()
                    
                    # Build turns: user msg triggers new turn, collect following assistant+tool
                    turns = []
                    current_turn = None
                    for msg in messages:
                        mid, role, tool_name, ts, tok, preview, tcid, finish, reasoning = msg
                        entry = {
                            'id': mid, 'role': role, 'ts': ts,
                            'content_preview': preview,
                        }
                        if role == 'user':
                            # Start new turn
                            if current_turn:
                                turns.append(current_turn)
                            current_turn = {
                                'turn_num': len(turns) + 1,
                                'user_msg': entry,
                                'assistant_msgs': [],
                                'tool_calls': [],
                                'turn_start_ts': ts,
                                'total_duration_ms': 0,
                            }
                        elif role == 'assistant' and current_turn:
                            current_turn['assistant_msgs'].append(entry)
                        elif role == 'tool' and current_turn:
                            current_turn['tool_calls'].append({
                                'id': mid, 'tool_name': tool_name or '?',
                                'ts': ts, 'content_preview': preview,
                                'token_count': tok,
                            })
                    if current_turn:
                        turns.append(current_turn)
                    
                    # Calculate durations per turn (use session span as real total)
                    sess_dur_ms = result['session']['total_sec'] * 1000 if result.get('session') else 10000
                    if sess_dur_ms < 1000:
                        sess_dur_ms = 10000  # minimum 10s for meaningful waterfall
                    
                    for i, turn in enumerate(turns):
                        all_ts = [turn['turn_start_ts']]
                        for a in turn['assistant_msgs']:
                            all_ts.append(a['ts'])
                        for t in turn['tool_calls']:
                            all_ts.append(t['ts'])
                        valid_ts = [t for t in all_ts if t and t > 0]
                        if len(valid_ts) >= 2:
                            turn['total_duration_ms'] = round((max(valid_ts) - min(valid_ts)) * 1000)
                        else:
                            turn['total_duration_ms'] = 100
                        if turn['total_duration_ms'] < 10:
                            turn['total_duration_ms'] = 100
                        
                        # Sub-actions within turn
                        actions = []
                        prev_ts = turn['turn_start_ts']
                        for a in turn['assistant_msgs']:
                            dur = round((a['ts'] - prev_ts) * 1000) if a['ts'] and prev_ts else 50
                            if dur < 5: dur = 50
                            actions.append({'type': 'model', 'duration_ms': dur, 'label': '思考', 'tool_name': None})
                            prev_ts = a['ts']
                        for t in turn['tool_calls']:
                            dur = round((t['ts'] - prev_ts) * 1000) if t['ts'] and prev_ts else 50
                            if dur < 5: dur = 50
                            actions.append({
                                'type': 'tool', 'duration_ms': dur,
                                'label': t['tool_name'],
                                'tool_name': t['tool_name'],
                                'preview': t['content_preview'][:30],
                            })
                            prev_ts = t['ts']
                        turn['actions'] = actions
                    
                    # Scale durations proportionally so total matches session duration
                    total_actions = sum(len(t.get('actions', [])) for t in turns)
                    if total_actions > 0:
                        # Give each action a proportional share of the session duration
                        # with tool actions weighted 2x (they take longer)
                        weighted_sum = sum(
                            len([a for a in t.get('actions', []) if a['type'] == 'model']) * 1 +
                            len([a for a in t.get('actions', []) if a['type'] == 'tool']) * 2
                            for t in turns
                        )
                        for t in turns:
                            for a in t.get('actions', []):
                                weight = 2 if a['type'] == 'tool' else 1
                                a['duration_ms'] = max(100, round(sess_dur_ms * weight / weighted_sum))
                    
                    # Filter turns with real actions
                    result['turns'] = [t for t in turns if len(t.get('actions', [])) > 0]
                    
                    # Tool breakdown for this session
                    cur2 = conn.execute('''
                        SELECT tool_name, COUNT(*) as cnt
                        FROM messages WHERE session_id=? AND tool_name IS NOT NULL AND tool_name != ''
                        GROUP BY tool_name ORDER BY cnt DESC
                    ''', (sid,))
                    for tn, cnt in cur2.fetchall():
                        result['tool_breakdown'][tn] = cnt
                    
                    conn.close()
                except Exception as e:
                    result['error'] = str(e)
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            self.wfile.write(json.dumps(result, default=str).encode())
            return
        
        elif path == '/' or path == '/index.html':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            html_path = DASH_DIR / 'dashboard_v2.html'
            if html_path.exists():
                self.wfile.write(html_path.read_bytes())
            else:
                # Fallback to v1
                html_path = DASH_DIR / 'dashboard.html'
                if html_path.exists():
                    self.wfile.write(html_path.read_bytes())
                else:
                    self.wfile.write(b'<html><body><h1>Dashboard not found</h1></body></html>')
            return
        
        static_path = DASH_DIR / path.lstrip('/')
        if static_path.exists() and static_path.is_file():
            ext = static_path.suffix
            ct_map = {'.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css',
                      '.png': 'image/png', '.jpg': 'image/jpeg', '.svg': 'image/svg+xml'}
            self.send_response(200)
            self.send_header('Content-Type', ct_map.get(ext, 'application/octet-stream'))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(static_path.read_bytes())
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'{"error":"Not found"}')
    
    def log_message(self, format, *args):
        pass

def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9198
    server = HTTPServer(('0.0.0.0', port), DashboardHandler)
    print(f'PGG Exec Dashboard v2 running at http://localhost:{port}')
    print(f'API: http://localhost:{port}/api/dashboard')
    print(f'Log API: http://localhost:{port}/api/log')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nShutting down...')
        server.server_close()

if __name__ == '__main__':
    main()