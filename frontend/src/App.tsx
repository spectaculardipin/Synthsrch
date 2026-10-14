import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "./lib/api";
import type { Provider, SearchResult } from "./lib/types";
import { ChatView } from "./components/ChatView";
import { FilterPanel } from "./components/FilterPanel";
import { SettingsView } from "./views/SettingsView";
import { HistoryView } from "./views/HistoryView";

type View = "search" | "chat" | "settings" | "history";

const NAV: { id: View; label: string; hint: string }[] = [
  { id: "search", label: "Search", hint: "Search the web with any provider" },
  { id: "chat", label: "Chat", hint: "Export checked sources from search first" },
  { id: "history", label: "History", hint: "Past searches and sessions" },
  { id: "settings", label: "Settings", hint: "API keys and model" },
];

export default function App() {
  const [view, setView] = useState<View>("search");
  const [query, setQuery] = useState("");
  const [provider, setProvider] = useState<Provider>("tavily");
  const [count, setCount] = useState(12);
  const [rankStart, setRankStart] = useState(1);
  const [rankEnd, setRankEnd] = useState(20);
  const [keywords, setKeywords] = useState("");
  const [keywordMode, setKeywordMode] = useState<"ANY" | "ALL">("ANY");
  const [subtopic, setSubtopic] = useState("");
  const [within, setWithin] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [showing, setShowing] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showFilters, setShowFilters] = useState(false);

  // extract drawer
  const [active, setActive] = useState<SearchResult | null>(null);
  const [extractText, setExtractText] = useState("");
  const [extractMeta, setExtractMeta] = useState("");

  // chat
  const [sessionId, setSessionId] = useState("");
  const [topic, setTopic] = useState("");
  const [purpose, setPurpose] = useState("");
  const [domainKw, setDomainKw] = useState("");
  const [model, setModel] = useState("nvidia/nemotron-3.5-lightning-30b-a3b");
  const [models, setModels] = useState<string[]>([]);
  const [chatLog, setChatLog] = useState<{ role: string; content: string; reasoning?: string }[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [chatSourceIds, setChatSourceIds] = useState<string[]>([]);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    refreshModels();
  }, []);

  // Re-sync the model default when (re)entering chat — Settings may have
  // changed nim_model while we were away, and the mount-once fetch is stale.
  useEffect(() => {
    if (view === "chat") refreshModels(false);
  }, [view]);

  async function refreshModels(takeDefault = true) {
    try {
      const m = await api.models();
      setModels(m.models);
      if (takeDefault && m.default) setModel(m.default);
    } catch { /* offline: keep current */ }
  }

  const hasResults = results.length > 0;
  // Live local filter — typing here never triggers a paid re-search.
  const visibleResults = useMemo(() => {
    const w = within.trim().toLowerCase();
    if (!w) return results;
    return results.filter((r) => `${r.title}\n${r.snippet ?? ""}`.toLowerCase().includes(w));
  }, [results, within]);
  const canChat = sessionId !== "" || selected.size > 0;

  function go(v: View) {
    if (v === "chat" && !canChat) return;
    setView(v);
  }

  async function doSearch(subtopics: string[] = []) {
    if (!query.trim()) return;
    setLoading(true); setError("");
    try {
      const kw = keywords.split(",").map((s) => s.trim()).filter(Boolean);
      const res = await api.search({
        query, provider, count,
        rank_start: rankStart, rank_end: rankEnd,
        keywords: kw, keyword_mode: keywordMode,
        subtopics: subtopics.length ? subtopics : (subtopic ? [subtopic] : []),
      });
      // Store the full server list; the "within" box filters locally (no refetch).
      setResults(res.results); setShowing(res.showing);
      setTopic(query); setView("search");
    } catch (e) { setError(e instanceof Error ? e.message : String(e)); }
    finally { setLoading(false); }
  }

  async function openCard(r: SearchResult) {
    setActive(r); setExtractText("Extracting clean text…"); setExtractMeta("");
    try {
      const ex = await api.extract(r.url, r.id);
      setExtractText(ex.text); setExtractMeta(`${r.publisher} • ${ex.chars} chars • via ${ex.via}`);
    } catch (e) { setExtractText(e instanceof Error ? e.message : String(e)); }
  }

  function toggle(id: string) {
    setSelected((prev) => { const n = new Set(prev); if (n.has(id)) n.delete(id); else n.add(id); return n; });
  }

  async function exportToChat() {
    const ids = [...selected];
    if (!ids.length) return;
    const dk = domainKw.split(",").map((s) => s.trim()).filter(Boolean);
    const s = await api.createSession({ topic: topic || query, purpose: purpose || "Synthesize selected sources", domainKeywords: dk, sourceIds: ids, model });
    setSessionId(s.session_id);
    setChatSourceIds(ids);
    setChatLog([{ role: "system", content: `Session ${s.session_id} — ${ids.length} sources attached.` }]);
    setView("chat");
  }

  function stopChat() {
    abortRef.current?.abort();
  }

  async function sendChat(text: string) {
    const q = text.trim();
    if (!sessionId || !q || streaming) return;
    setChatLog((l) => [...l, { role: "user", content: q }]);
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    setStreaming(true);
    let acc = "";
    let think = "";
    setChatLog((l) => [...l, { role: "assistant", content: "" }]);
    try {
      const resp = await fetch(`/api/sessions/${sessionId}/chat`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: q, model }), signal: ctrl.signal,
      });
      if (!resp.ok) {
        const body = await resp.text().catch(() => "");
        setChatLog((l) => [...l, { role: "assistant", content: `Request failed (HTTP ${resp.status}): ${body.slice(0, 300)}` }]);
        return;
      }
      const reader = resp.body?.getReader();
      if (!reader) return;
      const dec = new TextDecoder();
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        for (const line of dec.decode(value).split("\n")) {
          if (!line.startsWith("data: ")) continue;
          const payload = line.slice(6).trim();
          if (payload === "[DONE]") return;
          try {
            const obj = JSON.parse(payload) as { delta?: string; reasoning?: string; error?: string };
            if (obj.error) { acc += `\n[error: ${obj.error}]`; }
            else if (obj.delta) acc += obj.delta;
            else if (obj.reasoning) think += obj.reasoning;
            else continue;
            setChatLog((l) => { const n = [...l]; n[n.length - 1] = { role: "assistant", content: acc, reasoning: think || undefined }; return n; });
          } catch { /* keep */ }
        }
      }
    } catch (e) {
      if ((e as Error).name !== "AbortError") {
        setChatLog((l) => [...l, { role: "assistant", content: `Request failed: ${e instanceof Error ? e.message : String(e)}` }]);
      }
    } finally {
      setStreaming(false);
      abortRef.current = null;
    }
  }

  const chatSources = chatSourceIds
    .map((id) => results.find((r) => r.id === id))
    .filter((r): r is SearchResult => Boolean(r));

  const filterPanel = showFilters ? (
    <FilterPanel provider={provider} setProvider={setProvider} count={count} setCount={setCount}
      rankStart={rankStart} setRankStart={setRankStart} rankEnd={rankEnd} setRankEnd={setRankEnd}
      keywords={keywords} setKeywords={setKeywords} keywordMode={keywordMode} setKeywordMode={setKeywordMode}
      subtopic={subtopic} setSubtopic={setSubtopic} />
  ) : null;

  return (
    <div className="min-h-screen bg-white">
      <header className="sticky top-0 z-20 flex items-center gap-4 px-6 py-2.5 border-b border-neutral-200 bg-white/90 backdrop-blur">
        <button onClick={() => setView("search")} className="font-serif text-2xl">Synthsrch</button>
        <nav className="flex gap-2 text-sm ml-auto" aria-label="Primary">
          {NAV.map((n) => {
            const disabled = n.id === "chat" && !canChat;
            return (
              <button key={n.id} title={disabled ? "Export checked sources from search to unlock chat" : n.hint}
                disabled={disabled} onClick={() => go(n.id)}
                className={`px-3 py-1 rounded-full border ${view === n.id ? "bg-neutral-900 text-white border-neutral-900" : "border-neutral-300"} ${disabled ? "opacity-40 cursor-not-allowed" : ""}`}>
                {n.label}
              </button>
            );
          })}
        </nav>
      </header>

      {view === "search" && !hasResults && (
        <main className="max-w-2xl mx-auto pt-28 px-6 text-center">
          <h1 className="font-serif text-5xl">Synthsrch</h1>
          <p className="italic text-neutral-500 mt-1">Learn without clutter.</p>
          <div className="flex gap-2 mt-8">
            <div className="relative flex-1">
              <input className="input-pill pr-10" placeholder="Type your Query" value={query} onChange={(e) => setQuery(e.target.value)} onKeyDown={(e) => e.key === "Enter" && doSearch()} aria-label="Search query" />
              <button onClick={() => doSearch()} className="absolute right-3 top-1/2 -translate-y-1/2" aria-label="Search">🔍</button>
            </div>
            <button onClick={() => setShowFilters((s) => !s)} className="border border-neutral-800 rounded-full w-11 h-11" aria-label="Filters">⚙</button>
          </div>
          {filterPanel}
          {error && <p role="alert" className="text-red-700 mt-4">{error} — check Settings for the {provider} key.</p>}
          {loading && <p className="mt-4 text-neutral-500">Searching {provider}…</p>}
          <p className="text-xs text-neutral-400 mt-6">Search → check sources → Export → Chat for grounded synthesis.</p>
        </main>
      )}

      {view === "search" && hasResults && (
        <main className="max-w-6xl mx-auto px-6 py-4">
          <div className="flex gap-2">
            <div className="relative flex-1">
              <input className="input-pill pr-10 bg-neutral-100" value={query} onChange={(e) => setQuery(e.target.value)} onKeyDown={(e) => e.key === "Enter" && doSearch()} aria-label="Search query" />
              <button onClick={() => doSearch()} className="absolute right-3 top-1/2 -translate-y-1/2" aria-label="Search">🔍</button>
            </div>
            <button onClick={() => setShowFilters((s) => !s)} className="border border-neutral-800 rounded-full w-11 h-11" aria-label="Filters">⚙</button>
          </div>
          {filterPanel}
          <div className="mt-2 max-w-md">
            <div className="relative">
              <input className="input-pill !py-1.5 text-sm" placeholder="Search within these results." value={within} onChange={(e) => setWithin(e.target.value)} aria-label="Search within results" />
              <button onClick={() => subtopic && doSearch([subtopic])} className="absolute right-3 top-1/2 -translate-y-1/2 text-sm" title="Re-query web for sub-topic">🔍</button>
            </div>
            {within.trim() && <p className="text-xs text-neutral-500 mt-1">Filtering {visibleResults.length} of {results.length} locally — no new search.</p>}
          </div>
          <div className="flex items-center gap-3 mt-3 text-sm text-neutral-600">
            <span>{showing}</span>
            {selected.size > 0 && <button onClick={exportToChat} className="ml-auto px-4 py-1.5 bg-neutral-900 text-white rounded-full">Export {selected.size} → Chat</button>}
          </div>
          {loading && <p className="mt-2 text-neutral-500">Searching…</p>}
          {error && <p role="alert" className="text-red-700 mt-2">{error}</p>}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mt-4">
            {visibleResults.map((r) => (
              <article key={r.id} className="card-note relative" onClick={() => openCard(r)}>
                <div className="flex items-start justify-between gap-2">
                  <span className="text-xs text-neutral-600 truncate">{r.publisher}</span>
                  <input type="checkbox" checked={selected.has(r.id)} onChange={() => toggle(r.id)} onClick={(e) => e.stopPropagation()} className="w-4 h-4 accent-black" aria-label={`Select ${r.title}`} />
                </div>
                <h3 className="font-serif text-lg leading-snug mt-2 line-clamp-3">{r.title || r.url}</h3>
                {r.snippet && <p className="text-sm text-neutral-600 mt-1 line-clamp-2">{r.snippet}</p>}
                <span className="absolute bottom-2 right-3 text-xs text-neutral-500">#{r.rank}</span>
              </article>
            ))}
          </div>
        </main>
      )}

      {active && (
        <div className="fixed inset-0 z-30 bg-black/30 flex justify-end" onClick={() => setActive(null)}>
          <div className="bg-white w-full max-w-xl h-full overflow-auto p-6" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-start gap-2">
              <div><h2 className="font-serif text-xl">{active.title}</h2><p className="text-xs text-neutral-500">{extractMeta}</p></div>
              <button onClick={() => setActive(null)} className="ml-auto border rounded-full px-3 py-1" aria-label="Close">✕</button>
            </div>
            <pre className="whitespace-pre-wrap text-sm mt-4 font-sans">{extractText}</pre>
          </div>
        </div>
      )}

      {view === "chat" && (
        <ChatView sessionId={sessionId} topic={topic} setTopic={setTopic}
          purpose={purpose} setPurpose={setPurpose} domainKw={domainKw} setDomainKw={setDomainKw}
          model={model} setModel={setModel} models={models} sources={chatSources}
          log={chatLog} streaming={streaming} onSend={(t) => sendChat(t)} onStop={stopChat}
          onBackToSearch={() => setView("search")} />
      )}

      {view === "settings" && <SettingsView onSaved={(m, list) => { setModel(m); if (list.length) setModels(list); }} />}
      {view === "history" && <HistoryView />}
    </div>
  );
}
