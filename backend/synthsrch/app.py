"""FastAPI app — localhost only, serves API + static frontend build."""
from __future__ import annotations

import asyncio
import json
import time
import uuid
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import select

from .chat import build_system_prompt, build_user_prompt, stream_chat
from .config import get_settings
from .db import init_db, session_factory
from .extract import LocalExtractor
from .models import Message, ResultCache, Search, Session, SettingKV
from .providers.base import SearchRequest, SearchResult, apply_keyword_filter, slice_rank
from .search_service import run_search

from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    await hydrate_settings_from_db()
    yield


async def hydrate_settings_from_db() -> int:
    """Load persisted SettingKV rows into the cached Settings object.

    Without this, keys saved via PUT /api/settings vanish on restart
    because Settings is rebuilt from env vars only. Returns count applied.
    """
    from sqlalchemy import select as sa_select

    s = get_settings()
    applied = 0
    try:
        async with session_factory()() as db:
            rows = (await db.execute(sa_select(SettingKV))).scalars().all()
    except Exception:
        return 0
    for row in rows:
        if hasattr(s, row.key) and row.value:
            setattr(s, row.key, row.value)
            applied += 1
    return applied


app = FastAPI(title="Synthsrch", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8765", "http://localhost:8765", "http://127.0.0.1:5173", "http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def err(code: str, message: str, status: int = 400):
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


@app.get("/api/health")
async def health():
    s = get_settings()
    return {"ok": True, "db": str(s.db_path), "nim_model": s.nim_model}


@app.get("/api/models")
async def models():
    return {"models": get_settings().NIM_MODELS, "default": get_settings().nim_model}


class SearchResponse(BaseModel):
    search_id: str
    provider: str
    results: list[SearchResult]
    showing: str


@app.post("/api/search")
async def search(req: SearchRequest):
    t0 = time.time()
    try:
        raw, provider = await run_search(req)
    except PermissionError as e:
        return err("MISSING_KEY", str(e), 401)
    except RuntimeError as e:
        return err("PROVIDER_ERROR", str(e), 502)
    except ValueError as e:
        return err("BAD_PROVIDER", str(e), 400)
    except Exception as e:
        # Transport/decoding failures from the provider (timeouts, 5xx, bad
        # JSON) must surface as a named provider error, never a bare 500.
        return err("PROVIDER_ERROR", f"{req.provider}: request failed ({type(e).__name__}: {e})", 502)

    # subtopic expansion is client-driven re-query; here apply keyword filter + rank slice
    filtered = apply_keyword_filter(raw, req.keywords, req.keyword_mode)
    # in-memory subtopic filter (search-within): keep results matching ANY subtopic if given
    if req.subtopics:
        subs = [s.lower() for s in req.subtopics if s.strip()]
        filtered = [r for r in filtered if any(s in f"{r.title}\n{r.snippet}".lower() for s in subs)] or filtered
    sliced = slice_rank(filtered, req.rank_start, req.effective_end())

    search_id = f"srch-{uuid.uuid4().hex[:12]}"
    async with session_factory()() as db:
        db.add(
            Search(
                id=search_id, query=req.query, provider=provider, count=req.count,
                rank_start=req.rank_start, rank_end=req.rank_end,
                keywords=json.dumps(req.keywords), keyword_mode=req.keyword_mode,
                subtopics=json.dumps(req.subtopics),
            )
        )
        # Upsert: result ids are deterministic (provider+url hash), so repeat
        # searches overlap. Blind INSERT 500s on UNIQUE constraint. Preserve
        # any previously extracted text when refreshing a cached row.
        for r in sliced:
            existing = await db.get(ResultCache, r.id)
            if existing is None:
                db.add(ResultCache(id=r.id, search_id=search_id, rank=r.rank, title=r.title, url=r.url,
                                   publisher=r.publisher, snippet=r.snippet, score=r.score))
            else:
                existing.search_id = search_id
                existing.rank = r.rank
                existing.title = r.title
                existing.url = r.url
                existing.publisher = r.publisher
                existing.snippet = r.snippet
                existing.score = r.score
        await db.commit()

    ms = int((time.time() - t0) * 1000)
    return SearchResponse(
        search_id=search_id, provider=provider, results=sliced,
        showing=f"Showing ranks {req.rank_start}–{req.effective_end()} of ~{len(filtered)} (provider: {provider}, {ms}ms)",
    )


class ExtractRequest(BaseModel):
    url: str
    search_id: str | None = None
    result_id: str | None = None


@app.post("/api/extract")
async def extract(req: ExtractRequest):
    ex = LocalExtractor()
    try:
        text, via = await ex.extract(req.url)
    except Exception as e:
        return err("EXTRACT_FAILED", f"extract failed ({e}). Try another source.", 502)
    if req.result_id:
        async with session_factory()() as db:
            row = await db.get(ResultCache, req.result_id)
            if row:
                row.extract_text = text
                row.extract_via = via
                await db.commit()
    from urllib.parse import urlparse
    return {"url": req.url, "publisher": urlparse(req.url).hostname or "", "chars": len(text), "via": via, "text": text}


class ChatCreate(BaseModel):
    topic: str
    purpose: str
    domainKeywords: list[str] = []
    sourceIds: list[str] = []
    model: str | None = None


@app.post("/api/sessions")
async def create_session(body: ChatCreate):
    sid = f"sess-{uuid.uuid4().hex[:12]}"
    async with session_factory()() as db:
        db.add(Session(id=sid, topic=body.topic, purpose=body.purpose,
                       domain_keywords=json.dumps(body.domainKeywords),
                       model=body.model or get_settings().nim_model,
                       source_ids=json.dumps(body.sourceIds)))
        await db.commit()
    return {"session_id": sid}


class ChatMessage(BaseModel):
    query: str
    sourceIds: list[str] | None = None
    model: str | None = None
    max_tokens: int = 4096


async def _gap_fill_extracts(pairs: list[tuple[str, str]]) -> list[tuple[str, str, str]]:
    """Fetch missing source texts via the fast local path, in parallel.

    Returns [(result_id, text, via)] for successes only; failures are skipped
    so one bad URL never blocks the chat.
    """
    ex = LocalExtractor()

    async def one(rid: str, url: str) -> tuple[str, str, str] | None:
        try:
            text, via = await ex.extract(url, allow_fallback=False)
            return (rid, text, via)
        except Exception:
            return None

    done = await asyncio.gather(*(one(rid, url) for rid, url in pairs))
    return [d for d in done if d is not None]


@app.post("/api/sessions/{sid}/chat")
async def chat(sid: str, body: ChatMessage):
    async with session_factory()() as db:
        sess = await db.get(Session, sid)
        if not sess:
            return err("NOT_FOUND", "session not found", 404)
        src_ids = body.sourceIds if body.sourceIds is not None else json.loads(sess.source_ids or "[]")
        sources: list[SearchResult] = []
        extracts: dict[str, str] = {}
        missing: list[tuple[str, str]] = []  # (result_id, url) without cached text
        for rid in src_ids[:10]:
            row = await db.get(ResultCache, rid)
            if not row:
                continue
            sources.append(SearchResult(id=row.id, title=row.title, url=row.url, publisher=row.publisher,
                                        rank=row.rank, score=row.score, snippet=row.snippet))
            if row.extract_text:
                extracts[row.id] = row.extract_text[: get_settings().extract_max_chars]
            elif row.url:
                missing.append((row.id, row.url))
        topic, purpose = sess.topic, sess.purpose
        kws = json.loads(sess.domain_keywords or "[]")
        model = body.model or sess.model or get_settings().nim_model
        db.add(Message(id=f"m-{uuid.uuid4().hex[:10]}", session_id=sid, role="user", content=body.query))
        # Safety net: guarantee excerpts for every source. The UI pre-extracts in
        # the background after export, but a fast Send (or reload) can beat it.
        # Fast path only (no browser fallback) to bound chat latency; failures
        # fall back to the search snippet for that source.
        if missing:
            filled = await _gap_fill_extracts(missing)
            for rid, text, via in filled:
                extracts[rid] = text[: get_settings().extract_max_chars]
                row = await db.get(ResultCache, rid)
                if row:
                    row.extract_text = extracts[rid]
                    row.extract_via = via
        await db.commit()

    system = build_system_prompt(topic, purpose, kws, len(sources))
    user = build_user_prompt(body.query, sources, extracts)

    async def gen():
        full: list[str] = []
        try:
            async for kind, text in stream_chat(model, system, user, body.max_tokens):
                if kind == "content":
                    full.append(text)
                    yield f"data: {json.dumps({'delta': text})}\n\n"
                else:
                    yield f"data: {json.dumps({'reasoning': text})}\n\n"
        except PermissionError as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': f'nim error: {e}'})}\n\n"
        finally:
            text = "".join(full)
            if text:
                async with session_factory()() as db2:
                    db2.add(Message(id=f"m-{uuid.uuid4().hex[:10]}", session_id=sid, role="assistant", content=text))
                    await db2.commit()
            yield "data: [DONE]\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.get("/api/history")
async def history():
    async with session_factory()() as db:
        searches = (await db.execute(select(Search).order_by(Search.created_at.desc()).limit(50))).scalars().all()
        sessions = (await db.execute(select(Session).order_by(Session.created_at.desc()).limit(50))).scalars().all()
    return {
        "searches": [{"id": s.id, "query": s.query, "provider": s.provider, "created_at": str(s.created_at)} for s in searches],
        "sessions": [{"id": s.id, "topic": s.topic, "model": s.model} for s in sessions],
    }


@app.get("/api/settings")
async def get_settings_api():
    s = get_settings()

    def mask(v: str) -> str:
        return (v[:4] + "***" + v[-2:]) if len(v) > 8 else ("***" if v else "")

    return {
        "nim_base_url": s.nim_base_url, "nim_model": s.nim_model, "models": s.NIM_MODELS,
        "keys_present": {
            "nim": bool(s.nim_api_key), "tavily": bool(s.tavily_api_key), "exa": bool(s.exa_api_key),
            "serper": bool(s.serper_api_key), "linkup": bool(s.linkup_api_key), "firecrawl": bool(s.firecrawl_api_key),
        },
        "keys_masked": {
            "nim": mask(s.nim_api_key), "tavily": mask(s.tavily_api_key), "exa": mask(s.exa_api_key),
            "serper": mask(s.serper_api_key), "linkup": mask(s.linkup_api_key), "firecrawl": mask(s.firecrawl_api_key),
        },
    }


class SettingsUpdate(BaseModel):
    nim_api_key: str | None = None
    nim_model: str | None = None
    tavily_api_key: str | None = None
    exa_api_key: str | None = None
    serper_api_key: str | None = None
    linkup_api_key: str | None = None
    firecrawl_api_key: str | None = None


@app.put("/api/settings")
async def put_settings(body: SettingsUpdate):
    # Guard: ignore None AND blank strings so a stray "" can't wipe a good key.
    updates = {k: v.strip() if isinstance(v, str) else v for k, v in body.model_dump(exclude_none=True).items()}
    updates = {k: v for k, v in updates.items() if v != "" and v is not None}
    async with session_factory()() as db:
        for k, v in updates.items():
            await db.merge(SettingKV(key=k, value=str(v)))
        await db.commit()
    # update live settings cache for this process
    s = get_settings()
    for k, v in updates.items():
        if hasattr(s, k):
            setattr(s, k, v)
    # Echo back full state so the UI can confirm per-key without a refetch.
    return await get_settings_api()


@app.get("/api/doctor")
async def doctor():
    import sys
    s = get_settings()
    return {"python": sys.version.split()[0], "db": str(s.db_path), "db_exists": s.db_path.exists(),
            "host": s.host, "port": s.port}


def _static_dir() -> Path:
    return Path(__file__).parent / "static"


try:
    if _static_dir().exists() and any(_static_dir().iterdir()):
        app.mount("/", StaticFiles(directory=str(_static_dir()), html=True), name="static")
except Exception:
    pass
