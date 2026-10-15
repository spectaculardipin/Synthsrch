import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import rehypeSanitize from "rehype-sanitize";
import remarkGfm from "remark-gfm";
import { safeUrl, splitCitations } from "../lib/chat";
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
  provider: string; setProvider: (s: string) => void;
  providers: string[];
  configuredModels: { provider: string; model: string; hasKey: boolean }[];
  sources: SearchResult[];
  statusById: Record<string, "working" | "done" | "error">;
  onRetryExtract: (s: SearchResult) => void;
  onOpenSources: () => void;
  extracting: boolean;
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
  const [showTop, setShowTop] = useState(true);
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
    if (!draft.trim() || p.streaming || p.extracting) return;
    p.onSend(draft.trim());
    setDraft("");
    requestAnimationFrame(() => {
      if (taRef.current) taRef.current.style.height = "auto";
      taRef.current?.focus();
    });
  }

  function autoresize(el: HTMLTextAreaElement) {
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 120) + "px";
  }

  const kwCount = p.domainKw.split(",").map((s) => s.trim()).filter(Boolean).length;
  const visibleLog = p.log.filter((m) => m.role !== "system");
  const grounded = p.sources.length > 0;

  return (
    <main className="mx-auto max-w-3xl px-4 sm:px-6 pb-4 flex flex-col h-full w-full min-h-0">
      {grounded && (
      <>
      {/* Collapse toggle for the whole upper area */}
      <div className="flex justify-end pt-2">
        <button onClick={() => setShowTop((s) => !s)} aria-expanded={showTop}
          aria-label={showTop ? "Hide session header and sources" : "Show session header and sources"}
          className="text-[11px] px-2.5 py-0.5 rounded-full border border-neutral-200 text-neutral-500 hover:border-neutral-800 hover:text-neutral-900 transition-colors">
          {showTop ? "Hide header ▲" : "Show header ▼"}
        </button>
      </div>
      <div className={`grid transition-all duration-300 ease-in-out ${showTop ? "grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0"}`}>
        <div className="overflow-hidden">
      {/* Slim thread header */}
      <div className="pt-1 pb-2 border-b border-neutral-200">
        <div className="flex items-baseline gap-2 flex-wrap">
          <h2 className="font-serif text-xl truncate">{p.topic || "New chat"}</h2>
          <span className="text-xs text-neutral-500">{p.sessionId ? `· ${p.sessionId}` : "· general mode"}</span>
          <button onClick={() => setShowContext((s) => !s)} aria-expanded={showContext}
            className="ml-auto text-xs px-3 py-1 rounded-full border border-neutral-300 hover:border-neutral-800">
            {showContext ? "Hide context" : "Context"}
          </button>
        </div>
        {!showContext && (
          <div className="flex gap-1.5 mt-2 flex-wrap items-center text-xs" aria-label="Synthesis context">
            {p.purpose && <Chip label={`Purpose: ${p.purpose}`} />}
            {kwCount > 0 && <Chip label={`${kwCount} keyword${kwCount > 1 ? "s" : ""}`} />}
            <ModelWidget provider={p.provider} model={p.model} configured={p.configuredModels}
              onPick={(prov, mod) => { p.setProvider(prov); p.setModel(mod); }} />
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
            <label className="block">LLM provider
              <select className="border border-neutral-300 rounded-lg px-2 py-1.5 w-full mt-1 focus:border-neutral-800 outline-none" value={p.provider} onChange={(e) => p.setProvider(e.target.value)} aria-label="LLM provider">
                {p.providers.map((pr) => <option key={pr} value={pr}>{pr}</option>)}
              </select>
            </label>
            <label className="block sm:col-span-2">Model (type any model ID)
              <input className="border border-neutral-300 rounded-lg px-2 py-1.5 w-full mt-1 focus:border-neutral-800 outline-none font-mono text-xs" value={p.model}
                onChange={(e) => p.setModel(e.target.value)} placeholder="e.g. anthropic/claude-sonnet-4, gpt-4o-mini, gemini-2.0-flash" aria-label="LLM model (free text)" />
              <span className="block text-[11px] text-neutral-400 mt-0.5">Auto-router: on rate limits or errors it silently falls back to your other keyed providers (set per-provider models in Settings).</span>
            </label>
          </div>
        )}
      </div>

      {/* Sources row: grounded when attached, general mode otherwise */}
      <div className="flex items-center gap-2 pt-2.5">
        {p.sources.length > 0 ? (
          <>
            <span className="text-xs text-neutral-500">{p.sources.length} sources</span>
            <button onClick={p.onOpenSources} className="text-xs px-3 py-1 rounded-full border border-neutral-300 hover:border-neutral-800" aria-label="Manage sources">
              Sources +/−
            </button>
          </>
        ) : (
          <>
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-neutral-100 border border-neutral-200 text-neutral-500">General mode · no sources</span>
            {p.sessionId ? (
              <button onClick={p.onOpenSources} className="text-xs px-3 py-1 rounded-full border border-neutral-300 hover:border-neutral-800" aria-label="Add sources">
                + Add sources
              </button>
            ) : (
              <button onClick={p.onBackToSearch} className="text-xs px-3 py-1 rounded-full border border-neutral-300 hover:border-neutral-800" aria-label="Search the web for sources">
                Search the web
              </button>
            )}
          </>
        )}
      </div>
      {p.sources.length > 0 && (
        <div className="flex gap-2 overflow-x-auto no-scrollbar py-2.5" role="list" aria-label="Grounded sources">
          {p.sources.map((s, i) => {
            const st = p.statusById[s.id] ?? "working";
            const badge =
              st === "done" ? <span className="text-green-700" title="Full text extracted">✓</span> :
              st === "error" ? <span className="text-red-600" title="Extraction failed — click to retry">✗</span> :
              <span className="text-amber-500" title="Extracting full text…">…</span>;
            const card = (
              <>
                <span className="text-[11px] font-mono text-neutral-500">[S{i + 1}] {s.publisher} {badge}</span>
                <span className="block text-xs truncate">{s.title || s.url}</span>
              </>
            );
            const cls = "shrink-0 max-w-56 border border-neutral-200 rounded-xl px-2.5 py-1.5 hover:border-neutral-800 bg-white text-left";
            return st === "error" ? (
              <button key={s.id} role="listitem" onClick={() => p.onRetryExtract(s)} title="Extraction failed — retry" className={cls}>{card}</button>
            ) : safeUrl(s.url) ? (
              <a key={s.id} role="listitem" href={s.url} target="_blank" rel="noreferrer" title={s.title} className={cls}>{card}</a>
            ) : (
              <span key={s.id} role="listitem" title={s.title} className={cls}>{card}</span>
            );
          })}
        </div>
      )}
        </div>
      </div>
      </>
      )}

      {/* Message stream — sources required to begin */}
      {grounded ? (
      <>
      <div ref={scrollRef} onScroll={onScroll} role="log" aria-live="polite" aria-label="Conversation"
        className="mt-2 flex-1 min-h-0 overflow-y-auto pr-1 no-scrollbar">
        {visibleLog.length === 0 && !p.streaming && (
          <div role="status" className="text-center pt-10 pb-6 px-4">
            <p className="font-serif text-3xl">Ask grounded in your sources</p>
            <p className="text-sm text-neutral-500 mt-2">
              Answers cite [S1] — every claim links back to evidence.
            </p>
            <p className="text-[11px] text-neutral-400 mt-4">
              {p.provider && p.model ? `${p.provider} · ${shortModel(p.model)}` : "Pick a model in Context anytime."} · Enter to send, Shift+Enter for a new line.
            </p>
          </div>
        )}
          {visibleLog.map((m, i) =>
            m.role === "notice" ? (
              <div key={i} className="flex justify-center py-1.5">
                <p role="status" className="max-w-[90%] text-center text-[11px] text-neutral-500 bg-neutral-100 border border-neutral-200 rounded-full px-3 py-1">
                  ⇄ {m.content}
                </p>
              </div>
            ) : m.role === "user" ? (
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
                <AssistantText text={m.content} streaming={p.streaming && i === visibleLog.length - 1 && !m.content && !m.reasoning} />
              </div>
            ),
          )}
          {p.streaming && <p className="shimmer text-xs text-neutral-500 py-1">Synthesizing…</p>}
        </div>

      {/* Docked composer — only with sources attached */}
      <div className="sticky bottom-0 pt-2 pb-1 bg-gradient-to-b from-transparent via-white/95 to-white">
        <div className="flex items-center gap-2 border border-neutral-300 rounded-2xl bg-white pl-4 pr-2 py-1.5 shadow-sm focus-within:border-neutral-900 focus-within:ring-1 focus-within:ring-neutral-900 transition-shadow">
          <textarea ref={taRef} rows={1} value={draft} disabled={p.extracting}
            onChange={(e) => { setDraft(e.target.value); autoresize(e.target); }}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
            placeholder={p.extracting ? "Extracting source texts…" : "Ask grounded on the sources above…"}
            aria-label="Chat message" className="flex-1 resize-none outline-none text-sm leading-5 max-h-[120px] bg-transparent disabled:text-neutral-400 placeholder:text-neutral-400 py-1.5" />
          {p.streaming ? (
            <button onClick={p.onStop} aria-label="Stop generating" title="Stop"
              className="w-8 h-8 shrink-0 rounded-full bg-neutral-900 text-white text-xs hover:bg-black transition-colors">■</button>
          ) : (
            <button onClick={send} disabled={!draft.trim() || p.extracting} aria-label="Send message" title="Send"
              className="w-8 h-8 shrink-0 rounded-full bg-neutral-900 text-white disabled:opacity-30 hover:bg-black transition-colors">↑</button>
          )}
        </div>
        <p className="pt-1 text-center text-[11px] text-neutral-400">{
          p.extracting
            ? `Extracting full text… ${p.sources.filter((s) => p.statusById[s.id] === "done").length}/${p.sources.length} ready`
            : "Grounded in your selected sources · citations [S1] link claims to evidence"
        }</p>
      </div>
      </>
      ) : (
      /* Blocked state — no sources: minimal, no header, no composer */
      <div role="status" className="flex-1 min-h-0 flex flex-col items-center justify-center text-center px-6">
        <p className="font-serif text-3xl">You haven't added any sources yet.</p>
        <p className="text-sm text-neutral-500 mt-2">Search for sources to begin the conversation.</p>
        <button onClick={p.onBackToSearch}
          className="mt-6 px-6 py-2.5 bg-neutral-900 text-white rounded-full text-sm hover:bg-black transition-colors">
          🔍 Search for sources
        </button>
      </div>
      )}
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

/** Minimal model switcher: pre-entered provider:model pairs only.
 *  Picking one sets BOTH provider and its own model, so a provider can never
 *  be called with another provider's model ID (a needless-fallback trigger). */
function ModelWidget({ provider, model, configured, onPick }: {
  provider: string; model: string;
  configured: { provider: string; model: string; hasKey: boolean }[];
  onPick: (provider: string, model: string) => void;
}) {
  const usable = configured.filter((c) => c.hasKey && c.model);
  if (!usable.length) {
    return <>{provider && <Chip label={provider} mono />}{model && <Chip label={shortModel(model)} mono />}</>;
  }
  const current = `${provider}:${model}`;
  return (
    <label className="inline-flex items-center gap-1 text-xs" title="Switch model (pre-entered in Settings)">
      <span className="text-neutral-400">model:</span>
      <select value={usable.some((c) => `${c.provider}:${c.model}` === current) ? current : ""}
        onChange={(e) => {
          const [prov, ...rest] = e.target.value.split(":");
          if (prov && rest.length) onPick(prov, rest.join(":"));
        }}
        aria-label="Switch model" className="max-w-56 truncate border border-neutral-300 rounded-full pl-2.5 pr-1 py-0.5 bg-white hover:border-neutral-800 outline-none font-mono text-[11px]">
        {!usable.some((c) => `${c.provider}:${c.model}` === current) && (
          <option value="">{provider}:{shortModel(model)} (custom)</option>
        )}
        {usable.map((c) => (
          <option key={`${c.provider}:${c.model}`} value={`${c.provider}:${c.model}`}>
            {c.provider}:{c.model}
          </option>
        ))}
      </select>
    </label>
  );
}

function shortModel(m: string) {
  const tail = m.split("/").pop() ?? m;
  return tail.length > 34 ? tail.slice(0, 34) + "…" : tail;
}

function AssistantText({ text, streaming }: { text: string; streaming: boolean }) {
  if (!text && streaming) return <span className="caret" aria-label="Generating" />;
  // Inline flow: text chunks render without <p> wrappers (p → fragment) so
  // [S1] badges stay glued to the sentence instead of breaking it into blocks.
  return (
    <div className="markdown-body text-[16px] leading-[1.63]">
      {splitCitations(text).map((part, i) =>
        "cite" in part ? (
          <sup key={i} title={`Source S${part.cite}`} className="cite-badge">[S{part.cite}]</sup>
        ) : (
          <MarkdownChunk key={i} text={part.text} />
        ),
      )}
      {streaming && <span className="caret" aria-hidden="true" />}
    </div>
  );
}

function MarkdownChunk({ text }: { text: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      rehypePlugins={[rehypeSanitize]}
      components={{ p: ({ children }) => <>{children}</> }}
    >
      {text}
    </ReactMarkdown>
  );
}
