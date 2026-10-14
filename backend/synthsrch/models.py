"""SQLite models — persistent history (restart-proof)."""
from __future__ import annotations

import datetime as dt

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


class Base(DeclarativeBase):
    pass


class Search(Base):
    __tablename__ = "searches"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    query: Mapped[str] = mapped_column(Text)
    provider: Mapped[str] = mapped_column(String(32))
    count: Mapped[int] = mapped_column(default=10)
    rank_start: Mapped[int] = mapped_column(default=1)
    rank_end: Mapped[int | None] = mapped_column(default=None)
    keywords: Mapped[str] = mapped_column(Text, default="[]")
    keyword_mode: Mapped[str] = mapped_column(String(8), default="ANY")
    subtopics: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[dt.datetime] = mapped_column(default=_now)


class ResultCache(Base):
    __tablename__ = "results_cache"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    search_id: Mapped[str] = mapped_column(ForeignKey("searches.id"))
    rank: Mapped[int] = mapped_column(default=0)
    title: Mapped[str] = mapped_column(Text, default="")
    url: Mapped[str] = mapped_column(Text, default="")
    publisher: Mapped[str] = mapped_column(String(256), default="")
    snippet: Mapped[str] = mapped_column(Text, default="")
    score: Mapped[float | None] = mapped_column(default=None)
    extract_text: Mapped[str | None] = mapped_column(Text, default=None)
    extract_via: Mapped[str | None] = mapped_column(String(32), default=None)


class Session(Base):
    __tablename__ = "sessions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    topic: Mapped[str] = mapped_column(Text, default="")
    purpose: Mapped[str] = mapped_column(Text, default="")
    domain_keywords: Mapped[str] = mapped_column(Text, default="[]")
    model: Mapped[str] = mapped_column(String(128), default="")
    source_ids: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[dt.datetime] = mapped_column(default=_now)


class Message(Base):
    __tablename__ = "messages"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"))
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(default=_now)


class SettingKV(Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")
