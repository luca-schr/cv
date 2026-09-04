import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { marked } from "marked";
import { api } from "../api.js";
import {
  loadUsedBasenames,
  rememberBasename,
  suggestedBasename,
  uniqueBasename,
} from "../naming.js";

const PROGRESS_PHASES = [
  { until: 22, step: "analyze", label: "Analyse et nettoyage de l'offre…" },
  { until: 38, step: "meta", label: "Extraction poste et entreprise…" },
  { until: 90, step: "adapt", label: "Adaptation du CV avec le LLM…" },
  { until: 97, step: "render", label: "Rendu markdown final…" },
];

export function useCvApp() {
  const profiles = ref([]);
  const selectedProfileId = ref(null);
  const jobText = ref("");
  const markdown = ref("");
  const filename = ref("");
  const filenameDirty = ref(false);
  const usedBasenames = ref(loadUsedBasenames());
  const useLlm = ref(true);
  const english = ref(false);
  const llmOk = ref(false);
  const llmLabel = ref("LLM : vérification…");
  const busy = ref(false);
  const busyKind = ref("");
  const progressPct = ref(0);
  const progressLabel = ref("Préparation…");
  const isBusy = computed(() => busy.value);
  const generating = computed(() => busy.value && busyKind.value === "generate");
  const result = ref(null);
  const history = ref([]);
  const toastMsg = ref("");
  const toastTimer = ref(null);
  const profileStatus = ref("loading");
  let progressTimer = null;

  const selectedProfile = computed(
    () => profiles.value.find((p) => p.id === selectedProfileId.value) || null
  );

  const headingTitle = computed(() => {
    const profile = selectedProfile.value;
    return (
      result.value?.job_detected_title ||
      result.value?.title ||
      profile?.data?.header?.title_default ||
      profile?.name ||
      "Profil"
    );
  });

  const companyName = computed(() => result.value?.job_label || "");

  const autoBasename = computed(() =>
    uniqueBasename(
      suggestedBasename(selectedProfile.value, companyName.value, english.value),
      usedBasenames.value
    )
  );

  const progressPhase = computed(() => {
    if (progressPct.value >= 100) {
      return { step: "render", label: "Terminé" };
    }
    return PROGRESS_PHASES.find((p) => progressPct.value <= p.until) || PROGRESS_PHASES.at(-1);
  });

  const renderedHtml = computed(() => {
    const raw = (markdown.value || "").trim();
    if (!raw) return "";
    const prepared = raw
      .replace(/\]\(assets\//g, "](/assets/")
      .replace(/src="assets\//g, 'src="/assets/');
    return marked.parse(prepared, { async: false });
  });

  const hasMarkdown = computed(() => markdown.value.trim().length > 0);

  const progressSteps = [
    { id: "analyze", label: "Analyse de l'offre" },
    { id: "meta", label: "Poste & entreprise" },
    { id: "adapt", label: "Adaptation LLM" },
    { id: "render", label: "Rendu markdown" },
  ];

  function stepState(id) {
    const order = progressSteps.map((s) => s.id);
    const current = progressPhase.value.step;
    const done =
      progressPct.value >= 100 ||
      (generating.value && order.indexOf(id) < order.indexOf(current));
    const active = generating.value && current === id && progressPct.value < 100;
    return { active, done };
  }

  function showToast(msg) {
    toastMsg.value = msg;
    clearTimeout(toastTimer.value);
    toastTimer.value = setTimeout(() => {
      toastMsg.value = "";
    }, 2500);
  }

  function applyFilenameSuggestion() {
    if (!filenameDirty.value) filename.value = autoBasename.value;
  }

  async function checkLlm() {
    try {
      const data = await api.llmStatus();
      llmOk.value = Boolean(data.server_ok && data.model_ready);
      llmLabel.value = llmOk.value
        ? `LLM · ${data.model}`
        : (data.message || "LLM indisponible").replace(/—/g, "·");
      if (!llmOk.value) useLlm.value = false;
    } catch {
      llmOk.value = false;
      useLlm.value = false;
      llmLabel.value = "LLM indisponible";
    }
  }

  async function loadProfileMarkdown(id) {
    if (!id) return;
    profileStatus.value = "loading";
    try {
      const data = await api.profileMarkdown(id);
      markdown.value = data.markdown;
      result.value = null;
      filenameDirty.value = false;
      applyFilenameSuggestion();
      profileStatus.value = "ok";
    } catch (err) {
      profileStatus.value = "error";
      throw err;
    }
  }

  async function loadProfiles() {
    profileStatus.value = "loading";
    try {
      const items = await api.profiles();
      profiles.value = items;
      const fallback = items.find((p) => p.is_default) || items[0];
      if (fallback && selectedProfileId.value == null) {
        selectedProfileId.value = fallback.id;
        await loadProfileMarkdown(fallback.id);
      } else {
        profileStatus.value = items.length ? "ok" : "error";
      }
    } catch (err) {
      profileStatus.value = "error";
      throw err;
    }
  }

  async function fetchHistory() {
    try {
      history.value = await api.generations();
    } catch {
      history.value = [];
    }
  }

  async function runBusy(kind, label, fn) {
    if (busy.value) return;
    busy.value = true;
    busyKind.value = kind;
    progressLabel.value = label;
    if (kind === "generate") {
      startProgress();
    } else {
      stopProgress();
      progressPct.value = 0;
    }
    try {
      await fn();
      if (kind === "generate") {
        finishProgress(true);
      } else {
        progressPct.value = 100;
        progressLabel.value = "Terminé";
      }
    } catch (err) {
      if (kind === "generate") finishProgress(false);
      else progressPct.value = 0;
      throw err;
    } finally {
      busy.value = false;
      busyKind.value = "";
    }
  }

  function stopProgress() {
    if (progressTimer) {
      clearInterval(progressTimer);
      progressTimer = null;
    }
  }

  function startProgress() {
    stopProgress();
    progressPct.value = 0;
    progressLabel.value = PROGRESS_PHASES[0].label;
    const started = Date.now();
    progressTimer = setInterval(() => {
      const phase =
        PROGRESS_PHASES.find((p) => progressPct.value <= p.until) || PROGRESS_PHASES.at(-1);
      const phaseIdx = PROGRESS_PHASES.indexOf(phase);
      const speeds = useLlm.value ? [0.35, 0.28, 0.12, 0.18] : [0.55, 0.35, 0.08, 0.12];
      const bump = speeds[phaseIdx] * (1 - progressPct.value / 100) * (0.85 + Math.random() * 0.3);
      progressPct.value = Math.min(96, progressPct.value + bump);
      if (Date.now() - started > 45000) {
        progressPct.value = Math.min(98, progressPct.value + 0.05);
      }
      progressLabel.value = phase.label;
    }, 280);
  }

  function finishProgress(success) {
    stopProgress();
    if (success) {
      progressPct.value = 100;
      progressLabel.value = "Terminé";
    } else {
      progressPct.value = 0;
    }
  }

  async function generate() {
    const text = jobText.value.trim();
    if (text.length < 10) {
      showToast("Colle une offre (min. 10 caractères).");
      return;
    }
    if (!selectedProfileId.value) {
      showToast("Choisis un profil.");
      return;
    }
    try {
      await runBusy("generate", PROGRESS_PHASES[0].label, async () => {
        const data = await api.createGeneration({
          profile_id: selectedProfileId.value,
          job_text: text,
          use_llm: useLlm.value,
          english: english.value,
        });
        result.value = data;
        markdown.value = data.markdown;
        filenameDirty.value = false;
        applyFilenameSuggestion();
        await fetchHistory();
        showToast("CV adapté.");
      });
    } catch (err) {
      showToast(err.message || "Erreur de génération.");
    } finally {
      checkLlm();
    }
  }

  async function openGeneration(id) {
    try {
      await runBusy("action", "Chargement du CV…", async () => {
        const data = await api.generation(id);
        result.value = data;
        markdown.value = data.markdown;
        selectedProfileId.value = data.profile_id;
        filenameDirty.value = false;
        applyFilenameSuggestion();
      });
    } catch (err) {
      showToast(err.message || "Génération introuvable.");
    }
  }

  async function deleteGeneration(id) {
    if (!confirm("Supprimer ce CV de l'historique ?")) return;
    try {
      await runBusy("action", "Suppression…", async () => {
        await api.deleteGeneration(id);
        if (result.value?.id === id) {
          result.value = null;
          await loadProfileMarkdown(selectedProfileId.value);
        }
        await fetchHistory();
        showToast("CV supprimé.");
      });
    } catch {
      showToast("Suppression impossible.");
    }
  }

  async function purgeHistory() {
    if (!confirm("Supprimer tous les CV de l'historique ?")) return;
    try {
      await runBusy("action", "Vidage de l'historique…", async () => {
        const data = await api.purgeGenerations();
        result.value = null;
        await loadProfileMarkdown(selectedProfileId.value);
        await fetchHistory();
        showToast(`${data.deleted_generations} CV supprimé(s).`);
      });
    } catch {
      showToast("Impossible de vider l'historique.");
    }
  }

  async function loadHistory() {
    try {
      await runBusy("action", "Chargement de l'historique…", fetchHistory);
    } catch {
      showToast("Historique indisponible.");
    }
  }

  function exportBasename() {
    const typed = filename.value.trim().replace(/\.md$|\.pdf$/gi, "");
    const next = uniqueBasename(typed || autoBasename.value, usedBasenames.value);
    filename.value = next;
    usedBasenames.value = rememberBasename(next, usedBasenames.value);
    return next;
  }

  function triggerDownload(blob, name) {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = name;
    a.click();
    URL.revokeObjectURL(a.href);
  }

  async function copyMarkdown() {
    const text = markdown.value.trim();
    if (!text) return;
    await navigator.clipboard.writeText(text);
    showToast("Markdown copié.");
  }

  function downloadMarkdown() {
    const text = markdown.value.trim();
    if (!text) return;
    const base = exportBasename();
    const blob = new Blob([text], { type: "text/markdown;charset=utf-8" });
    triggerDownload(blob, `${base}.md`);
    showToast("Markdown téléchargé.");
  }

  async function downloadPdf() {
    const text = markdown.value.trim();
    if (!text) {
      showToast("Rien à exporter.");
      return;
    }
    try {
      await runBusy("action", "Export du PDF…", async () => {
        const base = exportBasename();
        const res = await api.exportPdf(text, base);
        const blob = await res.blob();
        triggerDownload(blob, `${base}.pdf`);
        showToast("PDF téléchargé.");
      });
    } catch (err) {
      showToast(err.message || "PDF indisponible (Pandoc requis).");
    }
  }

  function selectProfile(id) {
    selectedProfileId.value = id;
    loadProfileMarkdown(id).catch((err) => showToast(err.message));
  }

  function onProfileSelect() {
    loadProfileMarkdown(selectedProfileId.value).catch((err) => showToast(err.message));
  }

  function onFilenameInput() {
    filenameDirty.value = true;
  }

  watch(autoBasename, applyFilenameSuggestion);

  onMounted(async () => {
    await checkLlm();
    try {
      await loadProfiles();
      await fetchHistory();
      applyFilenameSuggestion();
    } catch (err) {
      showToast(err.message || "Chargement impossible.");
    }
  });

  onUnmounted(() => {
    stopProgress();
    clearTimeout(toastTimer.value);
  });

  return {
    profiles,
    selectedProfileId,
    headingTitle,
    profileStatus,
    jobText,
    markdown,
    filename,
    useLlm,
    english,
    llmOk,
    llmLabel,
    isBusy,
    generating,
    progressPct,
    progressLabel,
    result,
    history,
    toastMsg,
    renderedHtml,
    hasMarkdown,
    progressSteps,
    stepState,
    generate,
    selectProfile,
    onProfileSelect,
    onFilenameInput,
    openGeneration,
    deleteGeneration,
    purgeHistory,
    copyMarkdown,
    downloadMarkdown,
    downloadPdf,
    loadHistory,
  };
}
