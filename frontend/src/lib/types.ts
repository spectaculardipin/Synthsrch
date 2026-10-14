export interface SearchResult {
  id: string;
  title: string;
  url: string;
  publisher: string;
  rank: number;
  score?: number | null;
  snippet?: string;
}

export type Provider = "tavily" | "exa" | "serper" | "linkup" | "firecrawl";

export const PROVIDERS: Provider[] = ["tavily", "exa", "serper", "linkup", "firecrawl"];

export function filterResults<T extends { title: string; snippet?: string }>(
  results: T[],
  keywords: string[],
  mode: "ANY" | "ALL",
): T[] {
  const kws = keywords.map((k) => k.trim().toLowerCase()).filter(Boolean);
  if (!kws.length) return results;
  return results.filter((r) => {
    const hay = `${r.title}\n${r.snippet ?? ""}`.toLowerCase();
    const hits = kws.filter((k) => hay.includes(k));
    return mode === "ALL" ? hits.length === kws.length : hits.length > 0;
  });
}

export function sliceRank<T>(results: T[], start: number, end: number): T[] {
  return results.slice(Math.max(0, start - 1), end);
}

/** Suggestion list always contains the current value, even a custom-typed model. */
export function modelOptions(models: string[], current: string): string[] {
  if (!current) return models;
  return models.includes(current) ? models : [...models, current];
}
