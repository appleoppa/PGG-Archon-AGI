from agent.pgg_remaining_gap_closure_gates import run_all, source_to_gate_matrix, genedb_quality_audit


def test_source_matrix_has_8_sources():
    out = source_to_gate_matrix()
    assert out['status'].startswith('WATCH')
    assert len(out['matrix']) == 8


def test_genedb_quality_audit_reads_db():
    out = genedb_quality_audit()
    assert out['total'] >= 1
    assert 'by_status' in out


def test_run_all_packetizes_all_gaps():
    out = run_all()
    assert out['status'] == 'WATCH_REMAINING_GAPS_PACKETIZED_NOT_CLOSED'
    assert set(out['outputs']) == {'source_to_gate','genedb_quality','autonomy_elapsed','external_benchmark','legal_e2e_correctness'}
