import { useState } from "react";
import type { SessionSummary } from "../lib/api";

interface Props {
  sessions: SessionSummary[];
  activeId: string;
  loading: boolean;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete: (id: string) => void;
  onClearAll: () => void;
}

export function ChatSidebar(p: Props) {
  const [confirmClear, setConfirmClear] = useState(false);

  return (
    <aside className="w-64 shrink-0 border-r border-neutral-200 h-full overflow-y-auto no-scrollbar flex flex-col" aria-label="Chat sessions">
      <div className="p-3">
        <button onClick={p.onNew} className="w-full px-3 py-2 bg-neutral-900 text-white rounded-full text-sm hover:bg-black transition-colors">
          + New chat
        </button>
      </div>
      {p.loading && <p className="px-4 text-xs text-neutral-500">Loading…</p>}
      {!p.loading && p.sessions.length === 0 && (
        <p className="px-4 text-xs text-neutral-500">No conversations yet. Export sources from search to start.</p>
      )}
      <ul className="px-2 pb-2 space-y-1 flex-1">
        {p.sessions.map((s) => {
          const active = s.id === p.activeId;
          return (
            <li key={s.id} className={`group flex items-center gap-1 rounded-lg px-2 py-1.5 text-sm ${active ? "bg-neutral-900 text-white" : "hover:bg-neutral-100"}`}>
              <button onClick={() => p.onSelect(s.id)} title={s.topic || s.id}
                className="flex-1 text-left truncate min-w-0">
                {s.topic || "Untitled"}
              </button>
              <button onClick={() => p.onDelete(s.id)} aria-label={`Delete ${s.topic || s.id}`} title="Delete this chat"
                className={`text-xs px-1.5 py-0.5 rounded shrink-0 ${active ? "text-neutral-300 hover:text-white" : "text-neutral-400 hover:text-red-600"} transition-colors`}>
                ✕
              </button>
            </li>
          );
        })}
      </ul>
      {p.sessions.length > 0 && (
        <div className="p-3 border-t border-neutral-200">
          {!confirmClear ? (
            <button onClick={() => setConfirmClear(true)}
              className="w-full text-xs px-3 py-1.5 rounded-full border border-neutral-300 text-neutral-500 hover:border-red-600 hover:text-red-600 transition-colors">
              Clear all chats
            </button>
          ) : (
            <div className="flex gap-1.5">
              <button onClick={() => { p.onClearAll(); setConfirmClear(false); }}
                className="flex-1 text-xs px-2 py-1.5 rounded-full bg-red-600 text-white hover:bg-red-700 transition-colors">
                Confirm delete all
              </button>
              <button onClick={() => setConfirmClear(false)} aria-label="Cancel"
                className="text-xs px-2.5 py-1.5 rounded-full border border-neutral-300">
                ✕
              </button>
            </div>
          )}
        </div>
      )}
    </aside>
  );
}
