from __future__ import annotations

from agent import pgg_archon_llm_mutual_constraint as mutual
from agent import pgg_archon_redteam_corpus_gen as corpus_gen
from agent import pgg_archon_super_evolution_card as se_card
from agent.pgg_archon_provider_benchmark import (
    default_pgg_model_providers,
    third_party_benchmark_judge_providers,
)


def _labels(rows):
    return {row[0] for row in rows}


def test_mimo_is_not_in_default_provider_benchmark_pool() -> None:
    assert "mimo_v25_pro_auditor" not in {p.provider_id for p in default_pgg_model_providers()}
    assert "agnes_ai" in {p.provider_id for p in default_pgg_model_providers()}
    assert {p.provider_id for p in third_party_benchmark_judge_providers()} == {"mimo_v25_pro_auditor"}


def test_mimo_is_not_in_processing_llm_pools() -> None:
    assert "mimo" not in _labels(corpus_gen.PROVIDERS)
    assert "mimo" not in _labels(mutual._PROVIDERS)
    assert "mimo" not in _labels(se_card._PROVIDERS)
    assert "agnes" in _labels(corpus_gen.PROVIDERS)
    assert "agnes" in _labels(mutual._PROVIDERS)
    assert "agnes" in _labels(se_card._PROVIDERS)


def test_mimo_is_reserved_in_third_party_judge_pools() -> None:
    assert "mimo" in _labels(corpus_gen.THIRD_PARTY_JUDGE_PROVIDERS)
    assert "mimo" in _labels(mutual._THIRD_PARTY_JUDGE_PROVIDERS)
    assert "mimo" in _labels(se_card._THIRD_PARTY_JUDGE_PROVIDERS)
