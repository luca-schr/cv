import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "./api";
import { buildBasename } from "./naming";
import type { LoadStatus, ProfileSummary } from "./types";

function labelOf(profile: ProfileSummary | null | undefined, english: boolean): string {
  if (!profile?.profile) return "";
  return english ? profile.profile.en || profile.profile.fr || "" : profile.profile.fr || "";
}

function errMessage(err: unknown, fallback: string): string {
  return err instanceof Error && err.message ? err.message : fallback;
}

export default function App() {
  const [profiles, setProfiles] = useState<ProfileSummary[]>([]);
  const [profileId, setProfileId] = useState("");
  const [english, setEnglish] = useState(false);
  const [markdown, setMarkdown] = useState("");
  const [title, setTitle] = useState("");
  const [filename, setFilename] = useState("");
  const [filenameDirty, setFilenameDirty] = useState(false);
  const [status, setStatus] = useState<LoadStatus>("loading");
  const [busy, setBusy] = useState(false);
  const [translating, setTranslating] = useState(false);
  const [toast, setToast] = useState("");
  const toastTimer = useRef<number | undefined>(undefined);

  const selected = profiles.find((p) => p.id === profileId) || null;
  const heading = title || labelOf(selected, english) || "Profil";
  const autoName = useMemo(
    () => buildBasename({ title: heading, english }),
    [heading, english]
  );

  const showToast = useCallback((msg: string) => {
    setToast(msg);
    window.clearTimeout(toastTimer.current);
    toastTimer.current = window.setTimeout(() => setToast(""), 2800);
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
          showToast(errMessage(err, "Chargement impossible"));
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
          showToast(errMessage(err, "Profil introuvable"));
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [profileId, english, showToast]);

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
      setFilenameDirty(false);
      showToast("PDF exporté (1 page)");
    } catch (err) {
      showToast(errMessage(err, "Export impossible"));
    } finally {
      setBusy(false);
    }
  }

  async function applyDefault() {
    if (!profileId || !markdown.trim()) return;
    setBusy(true);
    setTranslating(true);
    try {
      const result = await api.applyDefault(profileId, markdown, english ? "en" : "fr");
      if (result.translated) {
        showToast("Défaut enregistré, autre langue traduite");
      } else {
        showToast(result.error || "Défaut enregistré (traduction indisponible)");
      }
    } catch (err) {
      showToast(errMessage(err, "Enregistrement impossible"));
    } finally {
      setTranslating(false);
      setBusy(false);
    }
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <img src="/favicon.ico" alt="" className="brand-logo" width={32} height={32} />
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
              spellCheck={false}
              value={filename}
              placeholder="lucas-schrever-…"
              onChange={(e) => {
                setFilenameDirty(true);
                setFilename(e.target.value);
              }}
            />
          </label>
        </div>
        <textarea
          className="editor-field preview"
          rows={18}
          spellCheck={false}
          disabled={busy}
          value={markdown}
          onChange={(e) => setMarkdown(e.target.value)}
          placeholder="Markdown du CV"
        />
        <div className="editor-actions">
          <button
            type="button"
            className="btn-default"
            disabled={!profileId || !markdown.trim() || busy}
            onClick={applyDefault}
          >
            {translating ? "Traduction…" : "Appliquer défaut"}
          </button>
          <button type="button" className="btn-export" disabled={!markdown.trim() || busy} onClick={downloadPdf}>
            {busy && !translating ? "Export…" : "Exporter le PDF"}
          </button>
        </div>
      </section>

      {toast ? <div className="toast">{toast}</div> : null}
    </div>
  );
}
