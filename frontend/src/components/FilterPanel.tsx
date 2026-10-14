import { PROVIDERS, type Provider } from "../lib/types";

export function FilterPanel(props: {
  provider: Provider; setProvider: (p: Provider) => void;
  count: number; setCount: (n: number) => void;
  rankStart: number; setRankStart: (n: number) => void;
  rankEnd: number; setRankEnd: (n: number) => void;
  keywords: string; setKeywords: (s: string) => void;
  keywordMode: "ANY" | "ALL"; setKeywordMode: (m: "ANY" | "ALL") => void;
  subtopic: string; setSubtopic: (s: string) => void;
}) {
  const p = props;
  return (
    <div className="border rounded-2xl p-4 mt-3 grid grid-cols-2 md:grid-cols-4 gap-3 text-sm text-left bg-neutral-50">
      <label>Provider
        <select className="border rounded-lg px-2 py-1 w-full" value={p.provider} onChange={(e) => p.setProvider(e.target.value as Provider)}>
          {PROVIDERS.map((x) => <option key={x} value={x}>{x}</option>)}
        </select>
      </label>
      <label>Count<input type="number" min={1} max={100} className="border rounded-lg px-2 py-1 w-full" value={p.count} onChange={(e) => p.setCount(Number(e.target.value))} /></label>
      <label>Rank start<input type="number" min={1} className="border rounded-lg px-2 py-1 w-full" value={p.rankStart} onChange={(e) => p.setRankStart(Number(e.target.value))} /></label>
      <label>Rank end<input type="number" min={1} className="border rounded-lg px-2 py-1 w-full" value={p.rankEnd} onChange={(e) => p.setRankEnd(Number(e.target.value))} /></label>
      <label className="col-span-2">Keywords (comma)<input className="border rounded-lg px-2 py-1 w-full" value={p.keywords} onChange={(e) => p.setKeywords(e.target.value)} placeholder="emissions, tax" /></label>
      <label>Match<select className="border rounded-lg px-2 py-1 w-full" value={p.keywordMode} onChange={(e) => p.setKeywordMode(e.target.value as "ANY" | "ALL")}><option>ANY</option><option>ALL</option></select></label>
      <label>Sub-topic<input className="border rounded-lg px-2 py-1 w-full" value={p.subtopic} onChange={(e) => p.setSubtopic(e.target.value)} placeholder="search within" /></label>
    </div>
  );
}
