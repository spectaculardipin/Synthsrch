import { useEffect, useState } from "react";
import { api } from "../lib/api";

const KEY_FIELDS = ["groq_api_key", "tavily_api_key", "exa_api_key", "serper_api_key", "linkup_api_key", "firecrawl_api_key"] as const;
const PROVIDER_OF: Record<string, string> = {
  groq_api_key: "Groq (LLM)", tavily_api_key: "Tavily", exa_api_key: "Exa",
  serper_api_key: "Serper", linkup_api_key: "Linkup", firecrawl_api_key: "Firecrawl",
};

interface SettingsState {
  groq_model?: string;
  models?: string[];
  keys_present?: Record<string, boolean>;
  keys_masked?: Record<string, string>;
}

export function SettingsView({ onSaved }: { onSaved?: (groqModel: string, models: string[]) => void }) {
  const [form, setForm] = useState<Record<string, string>>({ groq_model: "", tavily_api_key: "", exa_api_key: "", serper_api_key: "", linkup_api_key: "", firecrawl_api_key: "", groq_api_key: "" });
  const [status, setStatus] = useState<SettingsState>({});
  const [msg, setMsg] = useState("Loading saved settings…");
  const [saving, setSaving] = useState(false);

  async function refresh() {
    try {
      const s = (await api.settings()) as unknown as SettingsState & { groq_model?: string };
      setStatus(s);
      setMsg(`Default model: ${s.groq_model ?? ""}`);
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
      if (updated.groq_model) onSaved?.(updated.groq_model, updated.models ?? []);
      setForm({ groq_model: "", tavily_api_key: "", exa_api_key: "", serper_api_key: "", linkup_api_key: "", firecrawl_api_key: "", groq_api_key: "" });
      setMsg("Saved. Keys are stored locally and survive restarts.");
    } catch (e) {
      setMsg(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  }

  const present = status.keys_present ?? {};
  const masked = status.keys_masked ?? {};

  return (
    <main className="max-w-2xl mx-auto px-6 py-4">
      <h2 className="font-serif text-2xl">Settings — BYO keys (stored locally)</h2>
      <p className="text-sm text-neutral-500" role="status">{msg}</p>
      <form onSubmit={(e) => { e.preventDefault(); save(); }}>
      <label className="block text-sm mt-3">groq_model (Groq chat model)
        <input className="border rounded-lg px-2 py-1 w-full" value={form.groq_model} onChange={(e) => setForm({ ...form, groq_model: e.target.value })} placeholder={status.groq_model ?? "llama-3.1-8b-instant"} />
      </label>
      {KEY_FIELDS.map((k) => {
        const short = k === "groq_api_key" ? "groq" : k.replace("_api_key", "");
        const isSet = present[short];
        return (
          <div key={k} className="mt-2">
            <label className="block text-sm">
              <span className="inline-flex items-center gap-2">
                {PROVIDER_OF[k]} key
                <span title={isSet ? `Saved (${masked[short] ?? ""})` : "Not set"} className={`text-xs px-2 py-0.5 rounded-full ${isSet ? "bg-green-100 text-green-800" : "bg-neutral-200 text-neutral-600"}`}>
                  {isSet ? `✓ set ${masked[short] ?? ""}` : "✗ missing"}
                </span>
              </span>
              <input type="password" autoComplete="off" className="border rounded-lg px-2 py-1 w-full mt-1" value={form[k]} onChange={(e) => setForm({ ...form, [k]: e.target.value })} placeholder={isSet ? "Saved — type a new value to replace" : "Paste key here"} />
            </label>
          </div>
        );
      })}
      <button type="submit" disabled={saving} className="mt-3 px-5 py-2 bg-neutral-900 text-white rounded-full disabled:opacity-50">
        {saving ? "Saving…" : "Save"}
      </button>
      </form>
      <p className="text-xs text-neutral-500 mt-2">Blank fields are ignored (they never overwrite saved keys). Get keys: Tavily app.tavily.com · Exa dashboard.exa.ai · Serper serper.dev · Linkup app.linkup.so · Firecrawl firecrawl.dev · Groq console.groq.com/keys</p>
    </main>
  );
}
