import { useEffect, useState } from "react";
import { getSettings, updateSettings } from "../api";
import type { VisionModelOption } from "../types";

interface Props {
  onClose: () => void;
}

export default function SettingsDialog({ onClose }: Props) {
  const [provider, setProvider] = useState("none");
  const [apiKey, setApiKey] = useState("");
  const [keySet, setKeySet] = useState(false);
  const [model, setModel] = useState("gpt-4.1-mini");
  const [modelOptions, setModelOptions] = useState<VisionModelOption[]>([]);
  const [customModel, setCustomModel] = useState(false);
  const [detail, setDetail] = useState("high");
  const [ebayAppId, setEbayAppId] = useState("");
  const [ebayCertId, setEbayCertId] = useState("");
  const [ebayConfigured, setEbayConfigured] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    void (async () => {
      try {
        const settings = await getSettings();
        setProvider(settings.vision_provider);
        setKeySet(settings.openai_api_key_set);
        setModel(settings.openai_vision_model);
        setModelOptions(settings.vision_model_options ?? []);
        setCustomModel(
          !(settings.vision_model_options ?? []).some(
            (option) => option.id === settings.openai_vision_model,
          ),
        );
        setDetail(settings.openai_vision_detail);
        setEbayConfigured(settings.market_sources?.ebay_browse === "configured");
      } catch (exc) {
        setStatus(String(exc instanceof Error ? exc.message : exc));
      }
    })();
  }, []);

  const save = async () => {
    setSaving(true);
    setStatus(null);
    try {
      const settings = await updateSettings({
        vision_provider: provider,
        ...(apiKey.trim() ? { openai_api_key: apiKey.trim() } : {}),
        openai_vision_model: model,
        openai_vision_detail: detail,
        ...(ebayAppId.trim() ? { ebay_app_id: ebayAppId.trim() } : {}),
        ...(ebayCertId.trim() ? { ebay_cert_id: ebayCertId.trim() } : {}),
      });
      setKeySet(settings.openai_api_key_set);
      setApiKey("");
      setEbayAppId("");
      setEbayCertId("");
      setEbayConfigured(settings.market_sources?.ebay_browse === "configured");
      setStatus("Saved. Settings are live immediately.");
    } catch (exc) {
      setStatus(String(exc instanceof Error ? exc.message : exc));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(event) => event.stopPropagation()}>
        <h2>AI vision settings</h2>
        <div className="field">
          <label>Vision provider</label>
          <select value={provider} onChange={(event) => setProvider(event.target.value)}>
            <option value="none">None (no external calls)</option>
            <option value="openai">OpenAI</option>
          </select>
        </div>
        <div className="field">
          <label>
            OpenAI API key {keySet ? "(a key is configured — leave blank to keep it)" : "(not set)"}
          </label>
          <input
            type="password"
            value={apiKey}
            placeholder={keySet ? "••••••••" : "sk-..."}
            onChange={(event) => setApiKey(event.target.value)}
            autoComplete="off"
          />
        </div>
        <div className="field">
          <label>Vision model</label>
          <select
            value={customModel ? "__custom__" : model}
            onChange={(event) => {
              if (event.target.value === "__custom__") {
                setCustomModel(true);
              } else {
                setCustomModel(false);
                setModel(event.target.value);
              }
            }}
          >
            {modelOptions.map((option) => (
              <option key={option.id} value={option.id}>
                {option.id}
                {option.recommended ? " ★" : ""}
                {option.estimated_usd_per_100_stamps !== null
                  ? ` — ~$${option.estimated_usd_per_100_stamps.toFixed(2)} / 100 stamps`
                  : ""}
              </option>
            ))}
            <option value="__custom__">Custom model…</option>
          </select>
          {customModel && (
            <input
              value={model}
              placeholder="exact OpenAI model id"
              onChange={(event) => setModel(event.target.value)}
              style={{ marginTop: 6 }}
            />
          )}
          {!customModel && (
            <p className="muted" style={{ margin: "6px 0 0", fontSize: 12 }}>
              {modelOptions.find((option) => option.id === model)?.note ?? ""}
            </p>
          )}
        </div>
        <div className="field">
          <label>Image detail</label>
          <select value={detail} onChange={(event) => setDetail(event.target.value)}>
            <option value="low">low (cheapest)</option>
            <option value="auto">auto</option>
            <option value="high">high (best)</option>
          </select>
        </div>
        <h2 style={{ marginTop: 18 }}>Market evidence sources</h2>
        <p className="muted" style={{ marginTop: 0 }}>
          Wikidata reference lookup is always on (no key). eBay Browse activates once App ID and
          Cert ID are set — keys are stored in the local .env only.
        </p>
        <div className="field">
          <label>
            eBay App ID {ebayConfigured ? "(configured — leave blank to keep)" : "(not set)"}
          </label>
          <input
            type="password"
            value={ebayAppId}
            placeholder={ebayConfigured ? "••••••••" : "App ID (Client ID)"}
            onChange={(event) => setEbayAppId(event.target.value)}
            autoComplete="off"
          />
        </div>
        <div className="field">
          <label>
            eBay Cert ID {ebayConfigured ? "(configured — leave blank to keep)" : "(not set)"}
          </label>
          <input
            type="password"
            value={ebayCertId}
            placeholder={ebayConfigured ? "••••••••" : "Cert ID (Client Secret)"}
            onChange={(event) => setEbayCertId(event.target.value)}
            autoComplete="off"
          />
        </div>
        {status && <p className="muted">{status}</p>}
        <div className="actions">
          <button onClick={onClose}>Close</button>
          <button className="primary" onClick={() => void save()} disabled={saving}>
            Save
          </button>
        </div>
      </div>
    </div>
  );
}
