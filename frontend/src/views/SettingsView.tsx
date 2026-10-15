import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { LLM_PROVIDERS } from "../lib/types";

const SEARCH_KEYS = ["tavily_api_key", "exa_api_key", "serper_api_key", "linkup_api_key", "firecrawl_api_key"] as const;
const LLM_KEYS = ["nim_api_key", "openai_api_key", "anthropic_api_key", "gemini_api_key", "openrouter_api_key"] as const;
const LABEL: Record<string, string> = {
  nim_api_key: "NVIDIA NIM", openai_api_key: "OpenAI", anthropic_api_key: "Anthropic",
  gemini_api_key: "Google Gemini", openrouter_api_key: "OpenRouter",
  tavily_api_key: "Tavily", exa_api_key: "Exa", serper_api_key: "Serper",
  linkup_api_key: "Linkup", firecrawl_api_key: "Firecrawl",
};
const KEY_HINT: Record<string, string> = {
  nim_api_key: "build.nvidia.com", openai_api_key: "platform.openai.com",
  anthropic_api_key: "console.anthropic.com", gemini_api_key: "Google AI Studio",
  openrouter_api_key: "openrouter.ai",
  tavily_api_key: "app.tavily.com", exa_api_key: "dashboard.exa.ai", serper_api_key: "serper.dev",
  linkup_api_key: "app.linkup.so", firecrawl_api_key: "firecrawl.dev",
};

interface SettingsState {
  nim_model?: string; llm_model?: string; llm_provider?: string; models?: string[];
  llm_models?: Record<string, string>;
  keys_present?: Record<string, boolean>; keys_masked?: Record<string, string>;
}

export function SettingsView({ onSaved }: { onSaved?: (model: string, models: string[], provider: string) => void }) {
  const [form, setForm] = useState<Record<string, string>>({ llm_model: "", llm_provider: "" });
  const [status, setStatus] = useState<SettingsState>({});
  const [msg, setMsg] = useState("Loading saved settings…");
  const [saving, setSaving] = useState(false);
  const [showKeys, setShowKeys] = useState<Record<string, boolean>>({});

  async function refresh() {
    try {
      const s = (await api.settings()) as unknown as SettingsState;
      setStatus(s);
      setMsg(`Active LLM: ${(s.llm_provider ?? "nim") + " · " + (s.llm_model || s.nim_model || "")}`);
    } catch {
      setMsg("Could not reach backend.");
    }
  }

  useEffect(() => { refresh(); }, []);

  async function save() {
    setSaving(true);
    try {
      const payload = Object.fromEntries(Object.entries(form).filter(([, v]) => v.trim() !== ""));
      const updated = (await api.saveSettings(payload)) as unknown as SettingsState;
      setStatus(updated);
      onSaved?.(updated.llm_model || updated.nim_model || "", updated.models ?? [], updated.llm_provider || "");
      setForm({});
      setMsg("Saved. Keys stay on this machine and survive restarts.");
    } catch (e) {
      setMsg(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  }

  const present = status.keys_present ?? {};
  const masked = status.keys_masked ?? {};
  const short = (k: string) => k.replace("_api_key", "");
  const set = (k: string, v: string) => setForm({ ...form, [k]: v });
  const llmSet = LLM_KEYS.filter((k) => present[short(k)]).length;
  const searchSet = SEARCH_KEYS.filter((k) => present[short(k)]).length;

  return (
    <main className="max-w-2xl mx-auto px-6 py-6">
      <h2 className="font-serif text-3xl">Settings</h2>
      <p className="text-sm text-neutral-500 mt-1" role="status">{msg}</p>

      <form onSubmit={(e) => { e.preventDefault(); save(); }}>
        <section className="mt-5 border border-neutral-200 rounded-2xl p-4 bg-white shadow-sm" aria-label="Default model">
          <h3 className="font-semibold text-sm">Chat models per provider</h3>
          <p className="text-xs text-neutral-500 mt-0.5">Pre-enter one model ID per provider. The auto-router tries your selected provider first, then falls back to the other keyed providers on rate limits or errors.</p>
          <label className="block mt-3 text-sm">
            <span className="text-xs font-medium text-neutral-600">Preferred provider</span>
            <select className="border border-neutral-300 rounded-xl px-2.5 py-2 w-full mt-1 outline-none focus:border-neutral-900" value={form.llm_provider ?? ""}
              onChange={(e) => set("llm_provider", e.target.value)} aria-label="Default LLM provider">
              <option value="">Keep ({status.llm_provider || "nim"})</option>
              {LLM_PROVIDERS.map((pr) => <option key={pr} value={pr}>{pr}</option>)}
            </select>
          </label>
          <div className="mt-2 divide-y divide-neutral-100">
            {(["nim", "openai", "anthropic", "gemini", "openrouter"] as const).map((pr) => {
              const fk = pr === "nim" ? "nim_model" : `${pr}_model`;
              const current = pr === "nim" ? status.nim_model : (status.llm_models as Record<string, string> | undefined)?.[pr];
              const hasKey = present[pr];
              return (
                <div key={pr} className="py-2 flex items-center gap-2">
                  <span className={`text-xs font-mono px-2 py-0.5 rounded-full shrink-0 ${hasKey ? "bg-green-100 text-green-800" : "bg-neutral-100 text-neutral-500"}`}>
                    {pr}
                  </span>
                  <input className="border border-neutral-300 rounded-xl px-2.5 py-1.5 w-full font-mono text-xs outline-none focus:border-neutral-900"
                    value={form[fk] ?? ""} onChange={(e) => set(fk, e.target.value)}
                    placeholder={current || (pr === "nim" ? "nvidia/…" : pr === "gemini" ? "gemini-2.0-flash" : "model-id")}
                    aria-label={`${pr} model ID`} />
                </div>
              );
            })}
          </div>
        </section>

        <section className="mt-4 border border-neutral-200 rounded-2xl p-4 bg-white shadow-sm" aria-label="LLM keys">
          <div className="flex items-baseline gap-2">
            <h3 className="font-semibold text-sm">LLM keys</h3>
            <span className="text-xs text-neutral-500">{llmSet}/{LLM_KEYS.length} set</span>
          </div>
          <div className="mt-2 divide-y divide-neutral-100">
            {LLM_KEYS.map((k) => (
              <KeyRow key={k} k={k} value={form[k] || ""} set={(v) => set(k, v)}
                isSet={present[short(k)]} masked={masked[short(k)]}
                revealed={!!showKeys[k]} toggle={() => setShowKeys({ ...showKeys, [k]: !showKeys[k] })} />
            ))}
          </div>
        </section>

        <section className="mt-4 border border-neutral-200 rounded-2xl p-4 bg-white shadow-sm" aria-label="Search keys">
          <div className="flex items-baseline gap-2">
            <h3 className="font-semibold text-sm">Search keys</h3>
            <span className="text-xs text-neutral-500">{searchSet}/{SEARCH_KEYS.length} set · auto-fallback needs ≥2</span>
          </div>
          <div className="mt-2 divide-y divide-neutral-100">
            {SEARCH_KEYS.map((k) => (
              <KeyRow key={k} k={k} value={form[k] || ""} set={(v) => set(k, v)}
                isSet={present[short(k)]} masked={masked[short(k)]}
                revealed={!!showKeys[k]} toggle={() => setShowKeys({ ...showKeys, [k]: !showKeys[k] })} />
            ))}
          </div>
        </section>

        <div className="sticky bottom-4 mt-4 flex items-center gap-3">
          <button type="submit" disabled={saving}
            className="px-6 py-2.5 bg-neutral-900 text-white rounded-full text-sm hover:bg-black disabled:opacity-50 shadow-md transition-colors">
            {saving ? "Saving…" : "Save changes"}
          </button>
          <span className="text-xs text-neutral-400">Blank fields never overwrite saved keys.</span>
        </div>
      </form>
    </main>
  );
}

function KeyRow({ k, value, set, isSet, masked, revealed, toggle }: {
  k: string; value: string; set: (v: string) => void;
  isSet?: boolean; masked?: string; revealed: boolean; toggle: () => void;
}) {
  return (
    <div className="py-2.5 flex items-center gap-2.5">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">{LABEL[k] || k}</span>
          <span title={isSet ? `Saved (${masked ?? ""})` : "Not set"}
            className={`text-[11px] px-2 py-0.5 rounded-full shrink-0 ${isSet ? "bg-green-100 text-green-800" : "bg-neutral-100 text-neutral-500"}`}>
            {isSet ? `● ${masked ?? "set"}` : "○ missing"}
          </span>
        </div>
        <div className="flex gap-1.5 mt-1.5">
          <input type={revealed ? "text" : "password"} autoComplete="off"
            className="border border-neutral-300 rounded-xl px-2.5 py-1.5 w-full text-sm font-mono outline-none focus:border-neutral-900"
            value={value} onChange={(e) => set(e.target.value)}
            placeholder={isSet ? "Saved — type a new value to replace" : `Paste key from ${KEY_HINT[k] || "provider"}`} aria-label={`${LABEL[k] || k} key`} />
          <button type="button" onClick={toggle} aria-label={revealed ? "Hide key" : "Show key"} title={revealed ? "Hide" : "Show"}
            className="text-xs px-2.5 border border-neutral-300 rounded-xl text-neutral-500 hover:border-neutral-800 shrink-0">
            {revealed ? "Hide" : "Show"}
          </button>
        </div>
      </div>
    </div>
  );
}
