import { useEffect, useState } from "react";
import { api } from "../lib/api";

export function HistoryView() {
  const [h, setH] = useState<{ searches: { id: string; query: string; provider: string }[]; sessions: { id: string; topic: string }[] }>({ searches: [], sessions: [] });
  useEffect(() => { api.history().then(setH).catch(() => {}); }, []);
  return (
    <main className="max-w-3xl mx-auto px-6 py-4">
      <h2 className="font-serif text-2xl">History (persistent)</h2>
      {!h.searches.length && !h.sessions.length && (
        <p className="text-sm text-neutral-500 mt-2">Nothing yet. Run a search, then export sources to chat — both are saved here across restarts.</p>
      )}
      <h3 className="font-medium mt-3">Searches</h3>
      <ul className="text-sm">{h.searches.map((s) => <li key={s.id} className="border-b py-1">{s.query} <span className="text-neutral-500">({s.provider})</span></li>)}</ul>
      <h3 className="font-medium mt-3">Sessions</h3>
      <ul className="text-sm">{h.sessions.map((s) => <li key={s.id} className="border-b py-1">{s.topic}</li>)}</ul>
    </main>
  );
}
