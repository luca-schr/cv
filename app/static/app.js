const $ = (sel) => document.querySelector(sel);

const jobText = $("#job-text");
const useLlm = $("#use-llm");
const english = $("#english");
const btnGenerate = $("#btn-generate");
const btnCopy = $("#btn-copy");
const btnDownload = $("#btn-download");
const btnDownloadPdf = $("#btn-download-pdf");
const btnRefresh = $("#btn-refresh");
const btnPurge = $("#btn-purge");
const btnDefault = $("#btn-default");
const statusPanel = $("#status");
const preview = $("#preview");
const defaultTitle = $("#default-title");
const previewHeading = $("#preview-heading");
const history = $("#history");
const toast = $("#toast");

const genProgress = $("#gen-progress");
const genProgressBar = $("#gen-progress-bar");
const genProgressLabel = $("#gen-progress-label");
const genProgressPct = $("#gen-progress-pct");
const genProgressTrack = genProgress?.querySelector(".gen-progress-track");
const genStepEls = () => [...document.querySelectorAll("#gen-progress-steps [data-step]")];

let lastTitle = "cv";
let lastCompany = "";
let lastGenerationId = null;
let isDefaultView = true;
let progressTimer = null;

const PROGRESS_PHASES = [
  { until: 22, step: "analyze", label: "Analyse et nettoyage de l'offre…" },
  { until: 38, step: "meta", label: "Extraction poste et entreprise…" },
  { until: 90, step: "adapt", label: "Adaptation du CV avec Ollama…" },
  { until: 97, step: "render", label: "Rendu markdown final…" },
];

function showToast(msg) {
  toast.textContent = msg;
  toast.classList.remove("hidden");
  setTimeout(() => toast.classList.add("hidden"), 2500);
}

function setGenerateBusy(loading) {
  btnGenerate.disabled = loading;
  jobText.disabled = loading;
  useLlm.disabled = loading || useLlm.disabled;
  english.disabled = loading;
  btnGenerate.textContent = loading ? "Génération en cours…" : "Générer le CV";
}

function phaseForPct(pct) {
  return PROGRESS_PHASES.find((p) => pct <= p.until) || PROGRESS_PHASES.at(-1);
}

function updateProgressUI(pct, forceDone = false) {
  const clamped = Math.min(100, Math.max(0, Math.round(pct)));
  const phase = forceDone
    ? { step: "render", label: "Terminé" }
    : phaseForPct(clamped);

  genProgressBar.style.width = `${clamped}%`;
  genProgressPct.textContent = `${clamped}%`;
  genProgressLabel.textContent = phase.label;
  if (genProgressTrack) {
    genProgressTrack.setAttribute("aria-valuenow", String(clamped));
  }

  genStepEls().forEach((el) => {
    const step = el.dataset.step;
    el.classList.remove("active", "done");
    if (forceDone || clamped >= 100) {
      el.classList.add("done");
    } else if (step === phase.step) {
      el.classList.add("active");
    } else {
      const phaseIdx = PROGRESS_PHASES.findIndex((p) => p.step === step);
      const currentIdx = PROGRESS_PHASES.findIndex((p) => p.step === phase.step);
      if (phaseIdx >= 0 && phaseIdx < currentIdx) el.classList.add("done");
    }
  });
}

function startProgressSimulation() {
  stopProgressSimulation();
  genProgress.classList.remove("hidden");
  let pct = 0;
  let started = Date.now();
  updateProgressUI(0);

  progressTimer = setInterval(() => {
    const elapsed = Date.now() - started;
    const phase = phaseForPct(pct);
    const phaseIdx = PROGRESS_PHASES.indexOf(phase);
    const baseSpeed = useLlm.checked ? [0.35, 0.28, 0.12, 0.18][phaseIdx] : [0.55, 0.35, 0.08, 0.12][phaseIdx];
    const decay = 1 - pct / 100;
    const bump = baseSpeed * decay * (0.85 + Math.random() * 0.3);
    pct = Math.min(96, pct + bump);
    if (elapsed > 45000) pct = Math.min(98, pct + 0.05);
    updateProgressUI(pct);
  }, 280);
}

function finishProgress(success) {
  stopProgressSimulation();
  if (success) {
    updateProgressUI(100, true);
    setTimeout(() => genProgress.classList.add("hidden"), 900);
  } else {
    genProgress.classList.add("hidden");
    updateProgressUI(0);
  }
}

function stopProgressSimulation() {
  if (progressTimer) {
    clearInterval(progressTimer);
    progressTimer = null;
  }
}

function renderWarnings(warnings) {
  const list = $("#warnings");
  if (!warnings?.length) {
    list.classList.add("hidden");
    list.innerHTML = "";
    return;
  }
  list.classList.remove("hidden");
  list.innerHTML = warnings.map((w) => `<li>${w}</li>`).join("");
}

function slugify(text) {
  const raw = String(text ?? "").trim();
  if (!raw) return "";
  return (
    raw
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/œ/gi, "oe")
      .replace(/æ/gi, "ae")
      .replace(/ß/g, "ss")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/-+/g, "-")
      .replace(/^-|-$/g, "")
      .slice(0, 40) || ""
  );
}

function normalizeBaseSlug(slug) {
  return (slug || "").replace(/^cv-+/, "").replace(/^-+/, "") || "master";
}

function shortenSlug(slug, maxLen) {
  const s = (slug || "").replace(/^-|-$/g, "");
  if (!s) return "";
  return s.length > maxLen ? s.slice(0, maxLen).replace(/-+$/g, "") : s;
}

function buildCvBasename(roleSlug, companySlug) {
  const role = normalizeBaseSlug(roleSlug);
  const company = shortenSlug(companySlug, 18);
  if (company && company !== "cv") {
    return `cv-${role}-${company}`;
  }
  return `cv-${role}`;
}

function getPreviewMarkdown() {
  return preview.value.trim();
}

function syncExportButtons() {
  const hasContent = getPreviewMarkdown().length > 0;
  btnCopy.disabled = !hasContent;
  btnDownload.disabled = !hasContent;
  btnDownloadPdf.disabled = !hasContent;
}

function nextDownloadFilename(basename, ext) {
  const storageKey = `cv-dl:${basename}.${ext}`;
  const version = parseInt(localStorage.getItem(storageKey) || "0", 10) + 1;
  localStorage.setItem(storageKey, String(version));
  if (version === 1) return `${basename}.${ext}`;
  return `${basename}-v${version}.${ext}`;
}

function triggerDownload(blob, filename) {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}

function showDefaultPreview(data) {
  isDefaultView = true;
  lastTitle = normalizeBaseSlug(slugify(data.title));
  lastCompany = "";
  lastGenerationId = null;

  previewHeading.textContent = "Aperçu CV";
  defaultTitle.textContent = `Profil master — ${data.title}`;
  preview.value = data.markdown;
  preview.classList.remove("mode-adapted");
  statusPanel.classList.add("hidden");
  renderWarnings([]);
  syncExportButtons();
}

function showResult(data) {
  isDefaultView = false;
  lastTitle = normalizeBaseSlug(slugify(data.title));
  lastCompany = slugify(data.job_label || "");
  lastGenerationId = data.id ?? null;

  previewHeading.textContent = "CV adapté";
  defaultTitle.textContent = "Modifiable avant export";
  $("#result-job-title").textContent = data.job_detected_title || "—";
  $("#result-title").textContent = data.title;
  $("#result-company").textContent = data.job_label || "—";
  $("#result-tags").textContent = data.detected_tags?.join(", ") || "—";
  $("#result-llm").textContent = data.llm_applied ? "Ollama" : "template statique";
  renderWarnings(data.warnings);
  preview.value = data.markdown;
  preview.classList.add("mode-adapted");
  statusPanel.classList.remove("hidden");
  syncExportButtons();
}

async function loadDefaultMarkdown() {
  try {
    const res = await fetch("/api/profiles/default/markdown");
    if (!res.ok) throw new Error("Profil par défaut introuvable");
    showDefaultPreview(await res.json());
  } catch (e) {
    preview.value = "";
    showToast(e.message);
    syncExportButtons();
  }
}

async function generate() {
  const text = jobText.value.trim();
  if (text.length < 10) {
    showToast("Colle une offre (min. 10 caractères).");
    return;
  }

  setGenerateBusy(true);
  startProgressSimulation();
  try {
    const res = await fetch("/api/generations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ job_text: text, use_llm: useLlm.checked, english: english.checked }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Erreur ${res.status}`);
    }
    const data = await res.json();
    finishProgress(true);
    showResult(data);
    loadHistory();
    showToast("CV généré.");
  } catch (e) {
    finishProgress(false);
    showToast(e.message || "Erreur de génération.");
  } finally {
    setGenerateBusy(false);
    checkOllama();
  }
}

async function loadGeneration(id) {
  const res = await fetch(`/api/generations/${id}`);
  if (!res.ok) return;
  showResult(await res.json());
  preview.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

async function loadHistory() {
  const res = await fetch("/api/generations");
  if (!res.ok) return;
  const items = await res.json();
  if (!items.length) {
    history.innerHTML = "<li class='muted'>Aucune génération.</li>";
    return;
  }
  history.innerHTML = items
    .map(
      (g) => `
    <li>
      <div class="history-main">
        <button type="button" data-id="${g.id}" class="history-open">${escapeHtml(g.title)}</button>
        <div class="date">${new Date(g.created_at).toLocaleString("fr-FR")}</div>
      </div>
      <div class="history-actions">
        <button type="button" class="btn-icon danger" data-del="${g.id}" title="Supprimer">✕</button>
      </div>
    </li>`
    )
    .join("");
  history.querySelectorAll(".history-open").forEach((btn) => {
    btn.addEventListener("click", () => loadGeneration(btn.dataset.id));
  });
  history.querySelectorAll("[data-del]").forEach((btn) => {
    btn.addEventListener("click", () => deleteGeneration(btn.dataset.del));
  });
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

btnGenerate.addEventListener("click", generate);
btnDefault.addEventListener("click", loadDefaultMarkdown);
preview.addEventListener("input", syncExportButtons);

btnCopy.addEventListener("click", async () => {
  const markdown = getPreviewMarkdown();
  if (!markdown) return;
  await navigator.clipboard.writeText(markdown);
  showToast("Markdown copié.");
});

btnDownload.addEventListener("click", () => {
  const markdown = getPreviewMarkdown();
  if (!markdown) return;
  const role = isDefaultView ? "master" : lastTitle;
  const company = isDefaultView ? "" : lastCompany;
  const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
  triggerDownload(blob, nextDownloadFilename(buildCvBasename(role, company), "md"));
});

async function downloadPdf() {
  const markdown = getPreviewMarkdown();
  if (!markdown) {
    showToast("Rien à exporter.");
    return;
  }
  try {
    const role = isDefaultView ? "master" : lastTitle;
    const company = isDefaultView ? "" : lastCompany;
    const basename = buildCvBasename(role, company);
    const res = await fetch("/api/export/pdf", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ markdown, filename: basename }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Erreur PDF ${res.status}`);
    }
    const blob = await res.blob();
    triggerDownload(blob, nextDownloadFilename(basename, "pdf"));
    showToast(`PDF téléchargé.`);
  } catch (e) {
    showToast(e.message || "PDF indisponible (Pandoc requis).");
  }
}

btnDownloadPdf.addEventListener("click", downloadPdf);

async function deleteGeneration(id) {
  if (!confirm("Supprimer ce CV de l'historique ?")) return;
  const res = await fetch(`/api/generations/${id}`, { method: "DELETE" });
  if (!res.ok) {
    showToast("Suppression impossible.");
    return;
  }
  if (String(lastGenerationId) === String(id)) {
    loadDefaultMarkdown();
  }
  loadHistory();
  showToast("CV supprimé.");
}

async function purgeHistory() {
  if (!confirm("Supprimer tous les CV de l'historique ?")) return;
  const res = await fetch("/api/generations", { method: "DELETE" });
  if (!res.ok) {
    showToast("Impossible de vider l'historique.");
    return;
  }
  const data = await res.json();
  loadDefaultMarkdown();
  loadHistory();
  showToast(`${data.deleted_generations} CV supprimé(s).`);
}

btnRefresh.addEventListener("click", loadHistory);
btnPurge.addEventListener("click", purgeHistory);

async function checkOllama() {
  const el = $("#ollama-status");
  try {
    const res = await fetch("/api/llm/status");
    const data = await res.json();
    const ok = data.server_ok && data.model_ready;
    el.textContent = ok ? `Ollama · ${data.model}` : data.message.replace(/—/g, "·");
    el.classList.remove("ok", "warn", "muted");
    el.classList.add(ok ? "ok" : "warn");
    useLlm.disabled = !ok;
    if (!ok) useLlm.checked = false;
  } catch {
    el.textContent = "Ollama indisponible";
    el.classList.remove("ok");
    el.classList.add("warn");
  }
}

checkOllama();
loadDefaultMarkdown();
loadHistory();
