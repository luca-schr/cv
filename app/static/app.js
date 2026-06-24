const $ = (sel) => document.querySelector(sel);

const jobText = $("#job-text");
const useLlm = $("#use-llm");
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
const history = $("#history");
const toast = $("#toast");

let lastMarkdown = "";
let lastTitle = "cv";
let lastGenerationId = null;
let isDefaultView = true;

function showToast(msg) {
  toast.textContent = msg;
  toast.classList.remove("hidden");
  setTimeout(() => toast.classList.add("hidden"), 2500);
}

function setLoading(loading) {
  btnGenerate.disabled = loading;
  btnGenerate.textContent = loading ? "Génération…" : "Générer";
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
  return (text || "cv")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 40) || "cv";
}

/** Incrémente v2, v3… si le même nom de base a déjà été téléchargé (localStorage). */
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
  lastMarkdown = data.markdown;
  lastTitle = slugify(data.title);
  lastGenerationId = null;
  btnDownloadPdf.disabled = false;

  defaultTitle.textContent = data.title;
  preview.textContent = data.markdown;
  preview.classList.remove("mode-adapted");
  statusPanel.classList.add("hidden");
  renderWarnings([]);
}

function showResult(data) {
  isDefaultView = false;
  lastMarkdown = data.markdown;
  lastTitle = slugify(data.title);
  lastGenerationId = data.id ?? null;
  btnDownloadPdf.disabled = !lastGenerationId;

  defaultTitle.textContent = "CV adapté à une offre";
  $("#result-title").textContent = data.title;
  $("#result-tags").textContent = data.detected_tags?.join(", ") || "—";
  $("#result-llm").textContent = data.llm_applied ? "appliqué" : "non (fallback tags)";
  renderWarnings(data.warnings);
  preview.textContent = data.markdown;
  preview.classList.add("mode-adapted");
  statusPanel.classList.remove("hidden");
}

async function loadDefaultMarkdown() {
  try {
    const res = await fetch("/api/profiles/default/markdown");
    if (!res.ok) throw new Error("Profil par défaut introuvable");
    showDefaultPreview(await res.json());
  } catch (e) {
    preview.textContent = "Impossible de charger le profil par défaut.";
    showToast(e.message);
  }
}

async function generate() {
  const text = jobText.value.trim();
  if (text.length < 10) {
    showToast("Colle une offre (min. 10 caractères).");
    return;
  }

  setLoading(true);
  try {
    const res = await fetch("/api/generations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ job_text: text, use_llm: useLlm.checked }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Erreur ${res.status}`);
    }
    const data = await res.json();
    showResult(data);
    loadHistory();
    showToast("CV généré.");
  } catch (e) {
    showToast(e.message || "Erreur de génération.");
  } finally {
    setLoading(false);
  }
}

async function loadGeneration(id) {
  const res = await fetch(`/api/generations/${id}`);
  if (!res.ok) return;
  showResult(await res.json());
  preview.scrollIntoView({ behavior: "smooth", block: "start" });
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
        <button type="button" data-id="${g.id}" class="history-open">${g.title}</button>
        <div class="date">${new Date(g.created_at).toLocaleString("fr-FR")}</div>
      </div>
      <div class="history-actions">
        <button type="button" class="btn-icon" data-pdf="${g.id}" data-slug="${slugify(g.title)}" title="PDF">PDF</button>
        <button type="button" class="btn-icon danger" data-del="${g.id}" title="Supprimer">✕</button>
      </div>
    </li>`
    )
    .join("");
  history.querySelectorAll(".history-open").forEach((btn) => {
    btn.addEventListener("click", () => loadGeneration(btn.dataset.id));
  });
  history.querySelectorAll("[data-pdf]").forEach((btn) => {
    btn.addEventListener("click", () => downloadPdf(btn.dataset.pdf, btn.dataset.slug));
  });
  history.querySelectorAll("[data-del]").forEach((btn) => {
    btn.addEventListener("click", () => deleteGeneration(btn.dataset.del));
  });
}

btnGenerate.addEventListener("click", generate);
btnDefault.addEventListener("click", loadDefaultMarkdown);

btnCopy.addEventListener("click", async () => {
  if (!lastMarkdown) return;
  await navigator.clipboard.writeText(lastMarkdown);
  showToast("Markdown copié.");
});

btnDownload.addEventListener("click", () => {
  if (!lastMarkdown) return;
  const suffix = isDefaultView ? "master" : lastTitle;
  const blob = new Blob([lastMarkdown], { type: "text/markdown;charset=utf-8" });
  triggerDownload(blob, nextDownloadFilename(`cv-${suffix}`, "md"));
});

async function downloadPdf(id, slug) {
  try {
    const url = id
      ? `/api/generations/${id}/pdf`
      : "/api/profiles/default/pdf";
    const res = await fetch(url);
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Erreur PDF ${res.status}`);
    }
    const blob = await res.blob();
    const base = id ? slug || lastTitle : isDefaultView ? "master" : lastTitle;
    const filename = nextDownloadFilename(`cv-${base}`, "pdf");
    triggerDownload(blob, filename);
    showToast(`PDF : ${filename}`);
  } catch (e) {
    showToast(e.message || "PDF indisponible (Pandoc/WeasyPrint ?).");
  }
}

btnDownloadPdf.addEventListener("click", () => {
  if (isDefaultView) downloadPdf();
  else downloadPdf(lastGenerationId);
});

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
    el.textContent = data.message;
    el.classList.remove("ok", "warn");
    el.classList.add(data.server_ok && data.model_ready ? "ok" : "warn");
    useLlm.disabled = !(data.server_ok && data.model_ready);
    if (!data.server_ok || !data.model_ready) useLlm.checked = false;
  } catch {
    el.textContent = "Ollama : statut indisponible";
    el.classList.add("warn");
  }
}

checkOllama();
loadDefaultMarkdown();
loadHistory();
