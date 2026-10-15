import { useState } from "react";
import { api } from "../lib/api";
import { safeUrl } from "../lib/chat";
import type { SearchResult } from "../lib/types";

/** Provider- or user-supplied URLs are untrusted: only http(s) becomes a
 *  link, anything else (javascript:, data:, …) renders as plain text. */
function SourceTitle({ s }: { s: SearchResult }) {
  const href = safeUrl(s.url);
  return href ? (
    <a href={href} target="_blank" rel="noreferrer" title={`Open: ${s.title || s.url}`}
      className="block truncate font-medium hover:underline">{s.title || s.url}</a>
  ) : (
    <span className="block truncate font-medium" title={s.title || s.url}>{s.title || s.url}</span>
  );
}

interface Props {
  open: boolean;
  onClose: () => void;
  sessionId: string;
  current: SearchResult[];
  currentIds: string[];
  lastResults: SearchResult[];
  onChanged: (sourceIds: string[], sources: SearchResult[]) => void;
}

export function SourcesDrawer(p: Props) {
  const [tab, setTab] = useState<"current" | "results" | "search" | "url">("current");
  const [q, setQ] = useState("");
  const [url, setUrl] = useState("");
  const [searching, setSearching] = useState(false);
  const [found, setFound] = useState<SearchResult[]>([]);
  const [msg, setMsg] = useState("");

  if (!p.open) return null;

  async function mutate(add: (string | { url: string })[], remove: string[]) {
    setMsg("Updating…");
    try {
      const r = await api.patchSources(p.sessionId, { add, remove });
      // Re-fetch detail to get full source objects (titles/publishers).
      const det = await api.sessionDetail(p.sessionId);
      p.onChanged(r.sourceIds, det.sources);
      setMsg(`Updated — ${r.sourceIds.length} sources.`);
    } catch (e) {
      setMsg(e instanceof Error ? e.message : String(e));
    }
  }

  async function newSearch() {
    if (!q.trim()) return;
    setSearching(true); setMsg("");
    try {
      const res = await api.search({ query: q.trim(), provider: "auto", count: 10, rank_start: 1 });
      setFound(res.results as SearchResult[]);
      setMsg(res.results.length ? `${res.results.length} found (via ${res.provider}). Click + to add.` : "No results.");
    } catch (e) {
      setMsg(e instanceof Error ? e.message : String(e));
    } finally {
      setSearching(false);
    }
  }

  const currentSet = new Set(p.currentIds);

  return (
    <div className="fixed inset-0 z-30 bg-black/30 flex justify-end" onClick={p.onClose} role="dialog" aria-label="Manage sources">
      <div className="bg-white w-full max-w-md h-full overflow-y-auto p-5" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center gap-2">
          <h2 className="font-serif text-xl">Sources</h2>
          <button onClick={p.onClose} className="ml-auto border rounded-full px-3 py-1" aria-label="Close">✕</button>
        </div>
        <div className="flex gap-1.5 mt-3 text-xs" role="tablist">
          {(["current", "results", "search", "url"] as const).map((t) => (
            <button key={t} role="tab" aria-selected={tab === t} onClick={() => setTab(t)}
              className={`px-3 py-1 rounded-full border ${tab === t ? "bg-neutral-900 text-white border-neutral-900" : "border-neutral-300"}`}>
              {t === "current" ? `Current (${p.current.length})` : t === "results" ? "Last results" : t === "search" ? "New search" : "Paste URL"}
            </button>
          ))}
        </div>
        <p className="text-xs text-neutral-500 mt-2" role="status">{msg}</p>

        {tab === "current" && (
          <ul className="mt-3 space-y-2">
            {p.current.map((s, i) => (
              <li key={s.id} className="border border-neutral-200 rounded-xl px-3 py-2 text-sm flex gap-2 items-start">
                <span className="font-mono text-[11px] text-neutral-500">[S{i + 1}]</span>
                <span className="flex-1 min-w-0">
                  <SourceTitle s={s} />
                  <span className="block truncate text-xs text-neutral-500">{s.publisher} · {s.url}</span>
                </span>
                <button onClick={() => mutate([], [s.id])} className="text-xs border rounded-full px-2 py-0.5 shrink-0" aria-label={`Remove ${s.title}`}>Remove</button>
              </li>
            ))}
            {p.current.length === 0 && <p className="text-sm text-neutral-500">No sources in this chat.</p>}
          </ul>
        )}

        {tab === "results" && (
          <ul className="mt-3 space-y-2">
            {p.lastResults.map((s) => (
              <li key={s.id} className="border border-neutral-200 rounded-xl px-3 py-2 text-sm flex gap-2 items-start">
                <span className="flex-1 min-w-0">
                  <SourceTitle s={s} />
                  <span className="block truncate text-xs text-neutral-500">{s.publisher}</span>
                </span>
                {currentSet.has(s.id)
                  ? <button onClick={() => mutate([], [s.id])} className="text-xs border rounded-full px-2 py-0.5 shrink-0">Remove</button>
                  : <button onClick={() => mutate([s.id], [])} className="text-xs px-2 py-0.5 bg-neutral-900 text-white rounded-full shrink-0">+ Add</button>}
              </li>
            ))}
            {p.lastResults.length === 0 && <p className="text-sm text-neutral-500">No search results cached yet. Search first, or use New search.</p>}
          </ul>
        )}

        {tab === "search" && (
          <div className="mt-3">
            <div className="flex gap-2">
              <input className="border border-neutral-300 rounded-full px-4 py-2 text-sm flex-1 outline-none" value={q}
                onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === "Enter" && newSearch()}
                placeholder="Search the web…" aria-label="New source search" />
              <button onClick={newSearch} disabled={searching} className="px-4 py-2 bg-neutral-900 text-white rounded-full text-sm disabled:opacity-50">
                {searching ? "…" : "Search"}
              </button>
            </div>
            <ul className="mt-3 space-y-2">
              {found.map((s) => (
                <li key={s.id} className="border border-neutral-200 rounded-xl px-3 py-2 text-sm flex gap-2 items-start">
                  <span className="flex-1 min-w-0">
                    <SourceTitle s={s} />
                    <span className="block truncate text-xs text-neutral-500">{s.publisher}</span>
                  </span>
                  <button onClick={() => mutate([s.id], [])} className="text-xs px-2 py-0.5 bg-neutral-900 text-white rounded-full shrink-0">+ Add</button>
                </li>
              ))}
            </ul>
          </div>
        )}

        {tab === "url" && (
          <div className="mt-3">
            <div className="flex gap-2">
              <input className="border border-neutral-300 rounded-full px-4 py-2 text-sm flex-1 outline-none font-mono" value={url}
                onChange={(e) => setUrl(e.target.value)} placeholder="https://…" aria-label="Paste URL" />
              <button onClick={() => { if (url.trim()) { mutate([{ url: url.trim() }], []); setUrl(""); } }}
                className="px-4 py-2 bg-neutral-900 text-white rounded-full text-sm">Add</button>
            </div>
            <p className="text-xs text-neutral-500 mt-2">Any public http(s) article. Text is extracted locally.</p>
          </div>
        )}
      </div>
    </div>
  );
}
