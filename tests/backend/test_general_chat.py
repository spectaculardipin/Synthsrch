"""General chat without sources — prompt must not demand citations."""
from synthsrch.chat import build_system_prompt_v2, build_user_prompt


def test_general_mode_needs_no_citations():
    p = build_system_prompt_v2("General chat", "Open questions", [], 0).lower()
    assert "no sources attached" in p
    assert "no citations required" in p


def test_grounded_mode_still_demands_citations():
    p = build_system_prompt_v2("Climate", "Compare", ["emissions"], 2).lower()
    assert "cite like [s1]" in p


def test_user_prompt_without_sources_is_query_only():
    u = build_user_prompt("hello there?", [], {})
    assert "hello there?" in u and "[S1]" not in u
