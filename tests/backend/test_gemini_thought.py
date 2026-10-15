"""Gemini thought parts must surface as reasoning, never answer body."""
import json

import httpx as _real_httpx

from synthsrch.llm.gemini import stream_gemini


def _sse_client(chunks):
    async def _h(request):
        async def _gen():
            for c in chunks:
                yield c.encode()

        return _real_httpx.Response(200, content=_gen(), headers={"content-type": "text/event-stream"})

    return _real_httpx.AsyncClient(transport=_real_httpx.MockTransport(_h), timeout=120.0)


async def test_thought_parts_yield_reasoning_not_content(monkeypatch):
    import synthsrch.config as cfg

    cfg.get_settings().gemini_api_key = "g-test"
    thinking = json.dumps({"candidates": [{"content": {"parts": [{"text": "planning the answer", "thought": True}]}}]})
    answer = json.dumps({"candidates": [{"content": {"parts": [{"text": "final answer"}]}}]})

    import synthsrch.llm.gemini as gmod
    import types

    real_httpx = gmod.httpx

    def fake_client(*a, **k):
        return _sse_client([f"data: {thinking}\n\n", f"data: {answer}\n\n"])

    monkeypatch.setattr(gmod, "httpx", types.SimpleNamespace(AsyncClient=fake_client))
    try:
        out = [(k, t) async for k, t in stream_gemini("gemini-2.0-flash", "s", "u", 64)]
    finally:
        monkeypatch.setattr(gmod, "httpx", real_httpx)
        cfg.get_settings().gemini_api_key = ""
    assert ("reasoning", "planning the answer") in out
    assert ("content", "planning the answer") not in out
    assert ("content", "final answer") in out
