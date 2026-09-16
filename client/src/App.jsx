import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "./api.js";
import { buildBasename, loadVersions, nextVersion, rememberVersion, stem } from "./naming.js";

function labelOf(profile, english) {
  return english ? profile?.profile?.en || profile?.profile?.fr : profile?.profile?.fr || "";
}

export default function App() {
  const [profiles, setProfiles] = useState([]);
  const [profileId, setProfileId] = useState("");
  const [english, setEnglish] = useState(false);
  const [company, setCompany] = useState("");
  const [version, setVersion] = useState(1);
  const [markdown, setMarkdown] = useState("");
  const [title, setTitle] = useState("");
  const [filename, setFilename] = useState("");
  const [filenameDirty, setFilenameDirty] = useState(false);
  const [status, setStatus] = useState("loading");
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState("");

  const selected = profiles.find((p) => p.id === profileId) || null;
  const heading = title || labelOf(selected, english) || "Profil";
  const autoStem = useMemo(
    () => stem({ title: heading, company, english }),
    [heading, company, english]
  );
  const autoName = useMemo(
    () => buildBasename({ title: heading, company, english }, version),
    [heading, company, english, version]
  );

  const showToast = useCallback((msg) => {
    setToast(msg);
    window.clearTimeout(showToast._t);
    showToast._t = window.setTimeout(() => setToast(""), 2800);
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const items = await api.profiles();
        if (cancelled) return;
        setProfiles(items);
        setProfileId(items[0]?.id || "");
        setStatus("ok");
      } catch (err) {
        if (!cancelled) {
          setStatus("error");
          showToast(err.message || "Chargement impossible");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [showToast]);

  useEffect(() => {
    if (!profileId) return;
    let cancelled = false;
    setStatus("loading");
    (async () => {
      try {
        const data = await api.profile(profileId, english ? "en" : "fr");
        if (cancelled) return;
        setTitle(data.title || "");
        setMarkdown(data.markdown || "");
        setFilenameDirty(false);
        setStatus("ok");
      } catch (err) {
        if (!cancelled) {
          setStatus("error");
          showToast(err.message || "Profil introuvable");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [profileId, english, showToast]);

  useEffect(() => {
    setVersion(nextVersion(autoStem, loadVersions()));
  }, [autoStem]);

  useEffect(() => {
    if (!filenameDirty) setFilename(autoName);
  }, [autoName, filenameDirty]);

  async function downloadPdf() {
    if (!markdown.trim()) return;
    setBusy(true);
    try {
      const res = await api.exportPdf(markdown, filename || autoName);
      const blob = await res.blob();
      const href = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = href;
      a.download = `${filename || autoName}.pdf`;
      a.click();
      URL.revokeObjectURL(href);
      rememberVersion(autoStem, version);
      setVersion(nextVersion(autoStem, loadVersions()));
      setFilenameDirty(false);
      showToast("PDF exporté (1 page)");
    } catch (err) {
      showToast(err.message || "Export impossible");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <img src="/favicon.ico" alt="" className="brand-logo" width="32" height="32" />
          <h1>CV</h1>
        </div>
        <label className="checkbox">
          <input
            type="checkbox"
            checked={english}
            disabled={busy}
            onChange={(e) => setEnglish(e.target.checked)}
          />
          English
        </label>
      </header>

      <section className="panel section-profiles">
        <div className="profile-bar">
          <h2>{heading}</h2>
          <div className="profile-select-wrap">
            <span
              className={`status-dot ${status}`}
              title={status === "ok" ? "Profil chargé" : status === "loading" ? "Chargement" : "Erreur"}
            />
            <select
              className="profile-select"
              value={profileId}
              disabled={busy || !profiles.length}
              onChange={(e) => setProfileId(e.target.value)}
            >
              {profiles.map((p) => (
                <option key={p.id} value={p.id}>
                  {labelOf(p, english)}
                </option>
              ))}
            </select>
          </div>
        </div>
      </section>

      <section className="panel editor-card">
        <div className="editor-col-head">
          <h2 className="editor-col-title">Markdown</h2>
          <label className="filename-field">
            <span className="sr-only">Nom du fichier</span>
            <input
              className="filename-input"
              spellCheck="false"
              value={filename}
              placeholder="lucas-schrever-…"
              onChange={(e) => {
                setFilenameDirty(true);
                setFilename(e.target.value);
              }}
            />
          </label>
        </div>
        <div className="meta-row">
          <label>
            Société
            <input
              value={company}
              disabled={busy}
              placeholder="defaut si vide"
              onChange={(e) => setCompany(e.target.value)}
            />
          </label>
          <label className="version-field">
            Version
            <input
              type="number"
              min="1"
              value={version}
              disabled={busy}
              onChange={(e) => {
                setVersion(Math.max(1, Number(e.target.value) || 1));
                setFilenameDirty(false);
              }}
            />
          </label>
        </div>
        <textarea
          className="editor-field preview"
          rows={18}
          spellCheck="false"
          disabled={busy}
          value={markdown}
          onChange={(e) => setMarkdown(e.target.value)}
          placeholder="Markdown du CV"
        />
        <button type="button" className="btn-export" disabled={!markdown.trim() || busy} onClick={downloadPdf}>
          {busy ? "Export…" : "Exporter le PDF"}
        </button>
      </section>

      {toast ? <div className="toast">{toast}</div> : null}
    </div>
  );
}
