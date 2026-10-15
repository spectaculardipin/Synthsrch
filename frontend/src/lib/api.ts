import type { Provider, SearchResult } from "./types";

async function j<T>(r: Response): Promise<T> {
  if (!r.ok) {
    const body = await r.json().catch(() => ({}));
    const msg = (body as { error?: { message?: string } }).error?.message ?? `HTTP ${r.status}`;
    throw new Error(msg);
  }
  return r.json() as Promise<T>;
}

export interface SessionSummary { id: string; topic: string; model: string; created_at?: string }
export interface SessionDetail {
  session_id: string; topic: string; purpose: string; domainKeywords: string[];
  model: string; provider: string; modelRef: string;
  sourceIds: string[]; sources: SearchResult[];
  messages: { role: string; content: string }[];
}

export const api = {
  search: (body: object) =>
    fetch("/api/search", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }).then(
      (r) => j<{ search_id: string; provider: Provider; results: SearchResult[]; showing: string }>(r),
    ),
  extract: (url: string, result_id?: string) =>
    fetch("/api/extract", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ url, result_id }) }).then(
      (r) => j<{ url: string; publisher: string; chars: number; via: string; text: string }>(r),
    ),
  createSession: (body: object) =>
    fetch("/api/sessions", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }).then(
      (r) => j<{ session_id: string }>(r),
    ),
  settings: () => fetch("/api/settings").then((r) => j<Record<string, unknown>>(r)),
  saveSettings: (body: object) =>
    fetch("/api/settings", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }).then((r) => j(r)),
  models: () => fetch("/api/models").then((r) => j<{ models: string[]; default: string; providers: string[]; provider: string; configured: { provider: string; model: string; hasKey: boolean }[] }>(r)),
  history: () => fetch("/api/history").then((r) => j<{ searches: { id: string; query: string; provider: string }[]; sessions: { id: string; topic: string }[] }>(r)),
  sessions: () => fetch("/api/sessions").then((r) => j<{ sessions: SessionSummary[] }>(r)),
  sessionDetail: (id: string) => fetch(`/api/sessions/${id}`).then((r) => j<SessionDetail>(r)),
  deleteSession: (id: string) => fetch(`/api/sessions/${id}`, { method: "DELETE" }).then((r) => j(r)),
  deleteAllSessions: () => fetch("/api/sessions", { method: "DELETE" }).then((r) => j(r)),
  patchSources: (id: string, body: { add?: (string | { url: string; title?: string })[]; remove?: string[] }) =>
    fetch(`/api/sessions/${id}/sources`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }).then(
      (r) => j<{ session_id: string; sourceIds: string[] }>(r),
    ),
};
