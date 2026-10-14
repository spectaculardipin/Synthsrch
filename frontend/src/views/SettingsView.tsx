import { useEffect, useState } from "react";
import { api } from "../lib/api";

const KEY_FIELDS = ["nim_api_key", "tavily_api_key", "exa_api_key", "serper_api_key", "linkup_api_key", "firecrawl_api_key"] as const;
const PROVIDER_OF: Record<string, string> = {
  nim_api_key: "NIM (LLM)", tavily_api_key: "Tavily", exa_api_key: "Exa",
  serper_api_key: "Serper", linkup_api_key: "Linkup", firecrawl_api_key: "Firecrawl",
};

interface SettingsState {
  nim_model?: string;
  models?: string[];
  keys_present?: Record<string, boolean>;
  keys_masked?: Record<string, string>;
}

export function SettingsView({ onSaved }: { onSaved?: (nimModel: string, models: string[]) => void }) {
  const [form, setForm] = useState<Record<string, string>>({ nim_model: "", tavily_api_key: "", exa_api_key: "", serper_api_key: "", linkup_api_key: "", firecrawl_api_key: "", nim_api_key: "" });
  const [status, setStatus] = useState<SettingsState>({});
  const [msg, setMsg] = useState("Loading saved settings…");
  const [saving, setSaving] = useState(false);

  async function refresh() {
    try {
      const s = (await api.settings()) as unknown as SettingsState & { nim_model?: string };
      setStatus(s);
      setMsg(`Default model: ${s.nim_model ?? ""}`);
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
      if (updated.nim_model) onSaved?.(updated.nim_model, updated.models ?? []);
      setForm({ nim_model: "", tavily_api_key: "", exa_api_key: "", serper_api_key: "", linkup_api_key: "", firecrawl_api_key: "", nim_api_key: "" });
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
      <label className="block text-sm mt-3">nim_model (NIM chat model)
        <input className="border rounded-lg px-2 py-1 w-full" value={form.nim_model} onChange={(e) => setForm({ ...form, nim_model: e.target.value })} placeholder={status.nim_model ?? "nvidia/nemotron-3.5-lightning-30b-a3b"} />
      </label>
      {KEY_FIELDS.map((k) => {
        const short = k === "nim_api_key" ? "nim" : k.replace("_api_key", "");
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
      <p className="text-xs text-neutral-500 mt-2">Blank fields are ignored (they never overwrite saved keys). Get keys: Tavily app.tavily.com · Exa dashboard.exa.ai · Serper serper.dev · Linkup app.linkup.so · Firecrawl firecrawl.dev · NIM build.nvidia.com</p>
    </main>
  );
}
