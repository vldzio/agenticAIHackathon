import { useState } from "react";
import { getDeviceId } from "../lib/storage";
import { Notice } from "../components/Notice";
import { useSettings } from "../state/settings";

export function SettingsPage() {
  const { mode, setMode, apiKey, setApiKey, forgetKey, liveReady } = useSettings();
  const [draft, setDraft] = useState(apiKey);
  const [reveal, setReveal] = useState(false);

  return (
    <div className="stack narrow">
      <h1>Settings</h1>

      <section className="card">
        <h2>Plan generation</h2>
        <div role="radiogroup" aria-label="Generation mode" className="radios">
          <label className={`radio ${mode === "mock" ? "radio-on" : ""}`}>
            <input type="radio" name="mode" checked={mode === "mock"} onChange={() => setMode("mock")} />
            <span>
              <strong>Simulated</strong>
              <span className="muted"> — built-in rules, no key needed. Great for trying the app.</span>
            </span>
          </label>
          <label className={`radio ${mode === "live" ? "radio-on" : ""}`}>
            <input type="radio" name="mode" checked={mode === "live"} onChange={() => setMode("live")} />
            <span>
              <strong>Live (Gemini)</strong>
              <span className="muted"> — plans written by Google Gemini using your own API key.</span>
            </span>
          </label>
        </div>

        {mode === "live" && (
          <div className="field">
            <label htmlFor="apikey">Gemini API key</label>
            <div className="row">
              <input
                id="apikey"
                type={reveal ? "text" : "password"}
                autoComplete="off"
                spellCheck={false}
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                aria-describedby="apikey-hint"
              />
              <button className="btn" type="button" onClick={() => setReveal((r) => !r)}>
                {reveal ? "Hide" : "Show"}
              </button>
            </div>
            <div className="row">
              <button className="btn btn-primary" type="button" onClick={() => setApiKey(draft)}>
                Save for this tab
              </button>
              <button
                className="btn"
                type="button"
                onClick={() => {
                  forgetKey();
                  setDraft("");
                }}
              >
                Forget key
              </button>
              {liveReady && <span className="muted">Key saved for this browser tab.</span>}
            </div>
            <p className="hint" id="apikey-hint">
              Get a free key at <a href="https://aistudio.google.com/app/apikey" target="_blank" rel="noreferrer">Google AI Studio</a>.
            </p>
          </div>
        )}
      </section>

      <Notice tone="info" title="How your key is handled">
        <ul className="bullets">
          <li>Kept in this tab's session storage only, and gone when you close the tab.</li>
          <li>Sent to the AetherFit server with each request so it can call Gemini for you.</li>
          <li>Never saved to the database, written to logs, or returned in any response.</li>
        </ul>
      </Notice>

      <section className="card">
        <h2>Your data</h2>
        <p className="small">
          Saved plans are tied to an anonymous ID stored in this browser (<code>{getDeviceId().slice(0, 8)}…</code>). There are no accounts yet, so clearing your browser data means losing access to saved plans — export a PDF or JSON to keep a copy.
        </p>
      </section>
    </div>
  );
}
