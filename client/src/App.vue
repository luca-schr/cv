<script setup>
import { ref, onMounted } from 'vue'
import {
  generateCvStream,
  exportPdfStream,
  fetchGenerations,
  fetchGeneration,
  fetchOllamaStatus,
  pingApi,
  waitForNewGeneration,
  withRetry,
} from './api/http.js'
import logoUrl from './assets/logo.png'

const GEN_STEPS = [
  { id: 'profile', label: 'Chargement du profil' },
  { id: 'analyze', label: 'Analyse de l\'offre (Ollama)' },
  { id: 'skills', label: 'Compétences de l\'offre' },
  { id: 'adapt', label: 'Adaptation du CV (Ollama)' },
  { id: 'markdown', label: 'Composition du markdown' },
  { id: 'pdf', label: 'Vérification PDF A4' },
  { id: 'compress', label: 'Compression (Ollama)' },
  { id: 'save', label: 'Sauvegarde' },
]

const PDF_STEPS = [
  { id: 'prepare', label: 'Préparation du document' },
  { id: 'convert', label: 'Conversion Pandoc + WeasyPrint' },
  { id: 'layout', label: 'Ajustement mise en page A4' },
  { id: 'pages', label: 'Contrôle du nombre de pages' },
  { id: 'done', label: 'Finalisation' },
]

const jobText = ref('')
const cvMarkdown = ref('')
const english = ref(false)
const temperature = ref(0.45)
const loading = ref(false)
const pdfLoading = ref(false)
const genLoader = ref(null)
const pdfLoader = ref(null)
const ollamaStatus = ref('Ollama : vérification…')
const ollamaState = ref('checking')
const toast = ref('')
const history = ref([])
const exportMeta = ref({ title: '', company: null, version: 1, filename: 'cv' })

let toastTimer = null

function showToast(msg) {
  toast.value = msg
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toast.value = '' }, 2800)
}

function initLoader(steps) {
  return {
    label: 'Démarrage…',
    pct: 0,
    steps: steps.map((s) => ({ ...s, status: 'pending' })),
  }
}

function applyProgress(loader, event, stepOrder) {
  if (!loader) return loader
  const idx = stepOrder.indexOf(event.step)
  const next = {
    ...loader,
    label: event.label,
    pct: event.pct ?? loader.pct,
    steps: loader.steps.map((s) => {
      const sIdx = stepOrder.indexOf(s.id)
      if (sIdx < 0) return s
      if (sIdx < idx) return { ...s, status: 'done' }
      if (s.id === event.step) return { ...s, status: 'active' }
      return { ...s, status: 'pending' }
    }),
  }
  return next
}

function finishLoader(loader) {
  if (!loader) return null
  return {
    ...loader,
    pct: 100,
    label: 'Terminé',
    steps: loader.steps.map((s) => ({ ...s, status: 'done' })),
  }
}

const genStepOrder = GEN_STEPS.map((s) => s.id)
const pdfStepOrder = PDF_STEPS.map((s) => s.id)

async function checkOllama() {
  ollamaState.value = 'checking'
  ollamaStatus.value = 'Ollama : vérification…'
  try {
    const data = await fetchOllamaStatus()
    ollamaStatus.value = data.message
    ollamaState.value = data.server_ok && data.model_ready ? 'ok' : 'error'
  } catch (e) {
    ollamaStatus.value = e.message || 'API indisponible'
    ollamaState.value = 'error'
  }
}

async function loadHistory() {
  try {
    history.value = await fetchGenerations()
  } catch {
    history.value = []
  }
}

function setExportMeta(data) {
  exportMeta.value = {
    title: data.title,
    company: data.company ?? null,
    version: data.version || 1,
    filename: data.filename || 'cv',
  }
}

async function onGenerate() {
  const text = jobText.value.trim()
  if (text.length < 10) {
    showToast('Colle une offre (min. 10 caractères).')
    return
  }
  const beforeId = history.value[0]?.id ?? 0
  const beforeMd = cvMarkdown.value
  loading.value = true
  genLoader.value = initLoader(GEN_STEPS)
  try {
    const data = await generateCvStream(
      {
        job_text: text,
        english: english.value,
        temperature: temperature.value,
      },
      (event) => {
        genLoader.value = applyProgress(genLoader.value, event, genStepOrder)
      },
    )
    genLoader.value = finishLoader(genLoader.value)
    cvMarkdown.value = data.markdown
    setExportMeta(data)
    if (data.warnings?.length) showToast(data.warnings.join(' · '))
    else showToast(`CV généré — ${data.filename}.pdf`)
    await loadHistory()
  } catch (e) {
    genLoader.value = {
      ...genLoader.value,
      label: 'Finalisation côté serveur…',
      pct: 90,
    }
    try {
      const data = await waitForNewGeneration(beforeId)
      if (data && data.markdown !== beforeMd) {
        genLoader.value = finishLoader(genLoader.value)
        cvMarkdown.value = data.markdown
        setExportMeta(data)
        await loadHistory()
        showToast(`CV récupéré (génération #${data.id}).`)
      } else {
        showToast(e.message || 'Erreur de génération.')
      }
    } catch {
      showToast(e.message || 'Erreur de génération.')
    }
  } finally {
    loading.value = false
    setTimeout(() => { genLoader.value = null }, 1200)
  }
}

async function onExportPdf() {
  if (!cvMarkdown.value.trim()) {
    showToast('Rien à exporter.')
    return
  }
  pdfLoading.value = true
  pdfLoader.value = initLoader(PDF_STEPS)
  try {
    const { blob, filename } = await exportPdfStream(
      {
        markdown: cvMarkdown.value,
        title: exportMeta.value.title,
        company: exportMeta.value.company,
        version: exportMeta.value.version,
        filename: exportMeta.value.filename,
      },
      (event) => {
        pdfLoader.value = applyProgress(pdfLoader.value, event, pdfStepOrder)
      },
    )
    pdfLoader.value = finishLoader(pdfLoader.value)
    triggerDownload(blob, filename)
    showToast(`PDF téléchargé — ${filename}`)
  } catch (e) {
    showToast(e.message || 'PDF indisponible.')
  } finally {
    pdfLoading.value = false
    setTimeout(() => { pdfLoader.value = null }, 1200)
  }
}

async function openGeneration(id) {
  try {
    const data = await fetchGeneration(id)
    cvMarkdown.value = data.markdown
    setExportMeta(data)
    showToast('Génération chargée.')
  } catch {
    showToast('Impossible de charger.')
  }
}

function triggerDownload(blob, filename) {
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = filename
  a.click()
  URL.revokeObjectURL(a.href)
}

function formatDate(iso) {
  return new Date(iso).toLocaleString('fr-FR')
}

onMounted(async () => {
  try {
    await withRetry(pingApi, { attempts: 8, delayMs: 1500 })
    await withRetry(checkOllama, { attempts: 3, delayMs: 1000 })
    await withRetry(loadHistory, { attempts: 3, delayMs: 1000 })
  } catch {
    ollamaStatus.value = 'Backend indisponible — ferme cv.db et relance uvicorn'
    ollamaState.value = 'error'
  }
})
</script>

<template>
  <div class="app-shell">
    <header class="topbar">
      <div class="brand">
        <img :src="logoUrl" alt="" class="brand-logo" width="32" height="32" />
        <div>
          <h1>CV Generator</h1>
          <p class="muted">Offre → CV adapté → PDF</p>
        </div>
      </div>
      <button
        type="button"
        class="ollama-pill"
        :class="`ollama-pill--${ollamaState}`"
        title="Cliquer pour revérifier"
        @click="checkOllama"
      >
        {{ ollamaStatus }}
      </button>
    </header>

    <div class="workspace">
      <section class="panel col-input">
        <h2>Fiche de poste</h2>
        <textarea
          v-model="jobText"
          class="editor-field"
          rows="16"
          placeholder="Intitulé, employeur, missions, stack…"
          :disabled="loading"
        />

        <div class="controls">
          <label class="checkbox">
            <input v-model="english" type="checkbox" :disabled="loading" />
            English
          </label>
          <label class="temp">
            Température {{ temperature.toFixed(2) }}
            <input
              v-model.number="temperature"
              type="range"
              min="0.2"
              max="0.8"
              step="0.05"
              :disabled="loading"
            />
          </label>
        </div>

        <div v-if="genLoader" class="task-loader">
          <div class="task-loader-head">
            <span class="task-loader-title">Génération</span>
            <span class="task-loader-pct">{{ genLoader.pct ?? 0 }}%</span>
          </div>
          <div class="task-loader-bar"><span :style="{ width: `${genLoader.pct ?? 0}%` }" /></div>
          <p class="task-loader-label">{{ genLoader.label }}</p>
          <ul class="task-loader-steps">
            <li
              v-for="step in genLoader.steps"
              :key="step.id"
              :class="`step--${step.status}`"
            >
              {{ step.label }}
            </li>
          </ul>
        </div>

        <button class="btn-action" type="button" :disabled="loading" @click="onGenerate">
          {{ loading ? 'Génération en cours…' : 'Générer CV' }}
        </button>
      </section>

      <section class="panel col-preview">
        <h2>CV généré</h2>
        <textarea
          v-model="cvMarkdown"
          class="editor-field"
          spellcheck="false"
          placeholder="Markdown du CV…"
        />
        <div class="controls controls--spacer" aria-hidden="true" />
        <p v-if="exportMeta.filename && cvMarkdown.trim()" class="export-name muted">
          Fichier : <strong>{{ exportMeta.filename }}.pdf</strong>
        </p>

        <div v-if="pdfLoader" class="task-loader">
          <div class="task-loader-head">
            <span class="task-loader-title">Export PDF</span>
            <span class="task-loader-pct">{{ pdfLoader.pct ?? 0 }}%</span>
          </div>
          <div class="task-loader-bar"><span :style="{ width: `${pdfLoader.pct ?? 0}%` }" /></div>
          <p class="task-loader-label">{{ pdfLoader.label }}</p>
          <ul class="task-loader-steps">
            <li
              v-for="step in pdfLoader.steps"
              :key="step.id"
              :class="`step--${step.status}`"
            >
              {{ step.label }}
            </li>
          </ul>
        </div>

        <button
          class="btn-action"
          type="button"
          :disabled="pdfLoading || !cvMarkdown.trim()"
          @click="onExportPdf"
        >
          {{ pdfLoading ? 'Export en cours…' : 'Télécharger PDF' }}
        </button>
      </section>
    </div>

    <section class="panel panel-history">
      <h2>Historique</h2>
      <ul v-if="history.length" class="history">
        <li v-for="g in history" :key="g.id">
          <button type="button" class="history-open" @click="openGeneration(g.id)">
            {{ g.title }}
            <span v-if="g.company" class="company">— {{ g.company }}</span>
            <span v-if="g.version > 1" class="version">v{{ g.version }}</span>
          </button>
          <span class="date">{{ formatDate(g.created_at) }} · {{ g.filename }}.pdf</span>
        </li>
      </ul>
      <p v-else class="muted">Aucune génération.</p>
    </section>

    <div v-if="toast" class="toast">{{ toast }}</div>
  </div>
</template>

<style src="./assets/app.css"></style>
