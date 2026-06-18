from agent.pgg_gene_scoring_pipeline import _repo_score


def test_repo_score_parses_github_host_not_substring():
    assert _repo_score("https://github.com/openai/evals") == 90
    assert _repo_score("github.com/appleoppa/pgg") == 90
    assert _repo_score("https://github.com/someone/random") == 40


def test_repo_score_rejects_embedded_github_substring():
    assert _repo_score("https://evil.example/github.com/openai/evals") == 25
    assert _repo_score("https://github.com.evil.example/openai/evals") == 25
