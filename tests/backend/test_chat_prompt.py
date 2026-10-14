from synthsrch.chat import build_system_prompt, build_user_prompt
from synthsrch.providers.base import SearchResult


def test_system_prompt_contains_structured_fields():
    p = build_system_prompt("Climate", "Compare policies", ["emissions", "tax"], 2)
    assert "Climate" in p and "Compare policies" in p
    assert "emissions" in p and "[S1]" in p and "[S2]" in p
    assert "cite" in p.lower()


def test_user_prompt_cites_sources():
    s = [SearchResult(id="tavily-a", title="T", url="https://a.com", publisher="a.com", rank=1, snippet="snip")]
    u = build_user_prompt("q?", s, {"tavily-a": "full text here"})
    assert "[S1]" in u and "full text here" in u
