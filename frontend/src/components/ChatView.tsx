import { useEffect, useRef, useState } from "react";
import { modelOptions } from "../lib/types";
import { splitCitations } from "../lib/chat";
import type { SearchResult } from "../lib/types";

export interface ChatMessage {
  role: string;
  content: string;
  reasoning?: string;
}

interface Props {
  sessionId: string;
  topic: string; setTopic: (s: string) => void;
  purpose: string; setPurpose: (s: string) => void;
  domainKw: string; setDomainKw: (s: string) => void;
  model: string; setModel: (s: string) => void;
  models: string[];
  sources: SearchResult[];
  log: ChatMessage[];
  streaming: boolean;
  onSend: (text: string) => void;
  onStop: () => void;
  onBackToSearch: () => void;
}

/**
 * Design contract (minimal, from ChatGPT/Claude/Perplexity study):
 * - Centered 768px column; user bubble right-aligned dark; assistant plain prose.
 * - Slim collapsible context bar (chips) instead of a 3-field form.
 * - Persistent sources rail above the thread (Perplexity pattern).
 * - Docked rounded composer with stop state; shimmer + caret while streaming.
 */
export function ChatView(p: Props) {
  const [draft, setDraft] = useState("");
  const [showContext, setShowContext] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const stickRef = useRef(true);
  const taRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll only when already near the bottom (don't yank readers up).
  useEffect(() => {
    const el = scrollRef.current;
    if (el && stickRef.current) el.scrollTop = el.scrollHeight;
  }, [p.log]);

  function onScroll() {
    const el = scrollRef.current;
    if (!el) return;
    stickRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < 120;
  }

  function send() {
    if (!draft.trim() || p.streaming) return;
    p.onSend(draft.trim());
    setDraft("");
    requestAnimationFrame(() => taRef.current?.focus());
  }

  const kwCount = p.domainKw.split(",").map((s) => s.trim()).filter(Boolean).length;

  return (
    <main className="mx-auto max-w-3xl px-4 sm:px-6 pb-8">
      {/* Slim thread header */}
      <div className="pt-4 pb-2 border-b border-neutral-200">
        <div className="flex items-baseline gap-2 flex-wrap">
          <h2 className="font-serif text-xl truncate">{p.topic || "New synthesis"}</h2>
          <span className="text-xs text-neutral-500">{p.sessionId ? `· ${p.sessionId}` : "· no session"}</span>
          <button onClick={() => setShowContext((s) => !s)} aria-expanded={showContext}
            className="ml-auto text-xs px-3 py-1 rounded-full border border-neutral-300 hover:border-neutral-800">
            {showContext ? "Hide context" : "Context"}
          </button>
        </div>
        {!showContext && (
          <div className="flex gap-1.5 mt-2 flex-wrap text-xs" aria-label="Synthesis context">
            {p.purpose && <Chip label={`Purpose: ${p.purpose}`} />}
            {kwCount > 0 && <Chip label={`${kwCount} keyword${kwCount > 1 ? "s" : ""}`} />}
            {p.model && <Chip label={shortModel(p.model)} mono />}
          </div>
        )}
        {showContext && (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 mt-3 text-sm">
            <label className="block">Topic
              <input className="border border-neutral-300 rounded-lg px-2 py-1.5 w-full mt-1 focus:border-neutral-800 outline-none" value={p.topic} onChange={(e) => p.setTopic(e.target.value)} />
            </label>
            <label className="block">Purpose
              <input className="border border-neutral-300 rounded-lg px-2 py-1.5 w-full mt-1 focus:border-neutral-800 outline-none" value={p.purpose} onChange={(e) => p.setPurpose(e.target.value)} placeholder="e.g. compare pricing" />
            </label>
            <label className="block">Domain keywords
              <input className="border border-neutral-300 rounded-lg px-2 py-1.5 w-full mt-1 focus:border-neutral-800 outline-none" value={p.domainKw} onChange={(e) => p.setDomainKw(e.target.value)} placeholder="comma, separated" />
            </label>
            <label className="block sm:col-span-3">Model (custom allowed)
              <input list="groq-model-list" className="border border-neutral-300 rounded-lg px-2 py-1.5 w-full mt-1 focus:border-neutral-800 outline-none font-mono text-xs" value={p.model}
                onChange={(e) => p.setModel(e.target.value)} placeholder="type or pick a Groq model" aria-label="Groq model (custom allowed)" />
              <datalist id="groq-model-list">
                {modelOptions(p.models, p.model).map((m) => <option key={m} value={m} />)}
              </datalist>
            </label>
          </div>
        )}
      </div>

      {/* Sources rail (Perplexity pattern: grounding stays visible) */}
      {p.sources.length > 0 && (
        <div className="flex gap-2 overflow-x-auto py-2.5" role="list" aria-label="Grounded sources">
          {p.sources.map((s, i) => (
            <a key={s.id} role="listitem" href={s.url} target="_blank" rel="noreferrer" title={s.title}
              className="shrink-0 max-w-56 border border-neutral-200 rounded-xl px-2.5 py-1.5 hover:border-neutral-800 bg-white">
              <span className="text-[11px] font-mono text-neutral-500">[S{i + 1}] {s.publisher}</span>
              <span className="block text-xs truncate">{s.title || s.url}</span>
            </a>
          ))}
        </div>
      )}

      {/* Message stream */}
      {!p.sessionId ? (
        <div role="status" className="text-center py-14">
          <p className="font-serif text-2xl">Where should we begin?</p>
          <p className="text-sm text-neutral-500 mt-2">Search first, check 2–5 source cards, then export them here.</p>
          <button onClick={p.onBackToSearch} className="mt-4 px-5 py-2 bg-neutral-900 text-white rounded-full text-sm">Go to Search</button>
        </div>
      ) : (
        <div ref={scrollRef} onScroll={onScroll} role="log" aria-live="polite" aria-label="Conversation"
          className="mt-2 h-[46vh] min-h-72 overflow-y-auto pr-1">
          {p.log.filter((m) => m.role !== "system").length === 0 && (
            <p className="text-sm text-neutral-400 text-center pt-10">Ask anything grounded in the sources above.</p>
          )}
          {p.log.filter((m) => m.role !== "system").map((m, i) =>
            m.role === "user" ? (
              <div key={i} className="flex justify-end py-1.5">
                <div className="max-w-[80%] bg-neutral-900 text-white rounded-2xl rounded-br-md px-4 py-2.5 text-[15px] leading-relaxed whitespace-pre-wrap">{m.content}</div>
              </div>
            ) : (
              <div key={i} className="py-2.5 max-w-full">
                {m.reasoning && (
                  <details className="mb-1.5 text-xs text-neutral-500" open={p.streaming && !m.content}>
                    <summary className="cursor-pointer select-none">Thinking…</summary>
                    <p className="whitespace-pre-wrap border-l-2 border-neutral-200 pl-2 mt-1">{m.reasoning}</p>
                  </details>
                )}
                <AssistantText text={m.content} streaming={p.streaming && i === p.log.filter((x) => x.role !== "system").length - 1 && !m.content && !m.reasoning} />
              </div>
            ),
          )}
          {p.streaming && <p className="shimmer text-xs text-neutral-500 py-1">Synthesizing…</p>}
        </div>
      )}

      {/* Docked composer */}
      <div className="sticky bottom-0 pt-3 pb-1 bg-gradient-to-b from-transparent via-white/90 to-white">
        <div className="flex items-end gap-2 border border-neutral-800 rounded-[28px] bg-white px-4 py-2 focus-within:ring-1 focus-within:ring-neutral-800">
          <textarea ref={taRef} rows={1} value={draft} disabled={!p.sessionId}
            onChange={(e) => { setDraft(e.target.value); e.target.style.height = "auto"; e.target.style.height = Math.min(e.target.scrollHeight, 160) + "px"; }}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
            placeholder={p.sessionId ? "Ask grounded on the sources above…" : "Export sources from search to start"}
            aria-label="Chat message" className="flex-1 resize-none outline-none text-[15px] leading-relaxed max-h-40 bg-transparent disabled:text-neutral-400" />
          {p.streaming ? (
            <button onClick={p.onStop} aria-label="Stop generating"
              className="w-9 h-9 shrink-0 rounded-full bg-neutral-900 text-white text-sm">■</button>
          ) : (
            <button onClick={send} disabled={!p.sessionId || !draft.trim()} aria-label="Send message"
              className="w-9 h-9 shrink-0 rounded-full bg-neutral-900 text-white disabled:opacity-30">↑</button>
          )}
        </div>
        <p className="pt-1.5 text-center text-[11px] text-neutral-400">Grounded in your selected sources · citations [S1] link claims to evidence</p>
      </div>
    </main>
  );
}

function Chip({ label, mono = false }: { label: string; mono?: boolean }) {
  return (
    <span className={`px-2.5 py-0.5 rounded-full bg-neutral-100 border border-neutral-200 text-neutral-600 ${mono ? "font-mono text-[11px]" : ""}`}>
      {label}
    </span>
  );
}

function shortModel(m: string) {
  const tail = m.split("/").pop() ?? m;
  return tail.length > 34 ? tail.slice(0, 34) + "…" : tail;
}

function AssistantText({ text, streaming }: { text: string; streaming: boolean }) {
  if (!text && streaming) return <span className="caret" aria-label="Generating" />;
  return (
    <p className="text-[16px] leading-[1.63] whitespace-pre-wrap">
      {splitCitations(text).map((part, i) =>
        "cite" in part ? (
          <sup key={i} title={`Source S${part.cite}`}
            className="font-mono text-[11px] bg-neutral-100 border border-neutral-300 rounded px-1 mx-0.5 whitespace-nowrap">[S{part.cite}]</sup>
        ) : (
          <span key={i}>{part.text}</span>
        ),
      )}
      {streaming && <span className="caret" aria-hidden="true" />}
    </p>
  );
}
