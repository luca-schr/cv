<script setup>
import { ref, watch, onMounted } from 'vue'
import {
  pingApi,
  fetchCategories,
  fetchProfiles,
  fetchProfile,
  fetchDefaultProfile,
  deleteProfile,
  analyzeJob,
  exportPdf,
  fetchOllamaStatus,
} from './api/http.js'
import { loadUiState, saveUiState } from './storage.js'

const saved = loadUiState()
const english = ref(saved.english)
const search = ref('')
const category = ref('')
const categories = ref([])
const profiles = ref([])
const selectedId = ref(saved.selectedId)
const jobText = ref(saved.jobText)
const cvMarkdown = ref(saved.cvMarkdown)
const exportFilename = ref(saved.exportFilename)
const loadingList = ref(false)
const loadingProfile = ref(false)
const analyzing = ref(false)
const pdfLoading = ref(false)
const adaptInfo = ref(null)
const exportNote = ref('')
const ollamaStatus = ref('Ollama : …')
const ollamaState = ref('checking')
const ollamaReady = ref(false)
const toast = ref('')
let toastTimer = null
let searchTimer = null
let persistReady = false

function showToast(msg) {
  toast.value = msg
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toast.value = '' }, 3600)
}

function normalizeFilename() {
  const name = (exportFilename.value || '')
    .replace(/\.pdf$/i, '')
    .trim()
  exportFilename.value = name || 'cv'
}

function persist() {
  if (!persistReady) return
  saveUiState({
    jobText: jobText.value,
    cvMarkdown: cvMarkdown.value,
    selectedId: selectedId.value,
    exportFilename: exportFilename.value,
    english: english.value,
  })
}

async function checkOllama() {
  ollamaState.value = 'checking'
  ollamaStatus.value = 'Ollama : vérification…'
  try {
    const data = await fetchOllamaStatus()
    ollamaReady.value = Boolean(data.server_ok && data.model_ready && data.enabled)
    ollamaStatus.value = data.message
    ollamaState.value = ollamaReady.value ? 'ok' : 'error'
  } catch (e) {
    ollamaReady.value = false
    ollamaStatus.value = e.message || 'Ollama indisponible'
    ollamaState.value = 'error'
  }
}

async function loadCategories() {
  const data = await fetchCategories()
  categories.value = data.items || []
}

async function loadProfiles() {
  loadingList.value = true
  try {
    const data = await fetchProfiles({
      q: search.value.trim(),
      category: category.value,
    })
    profiles.value = data.items || []
  } catch (e) {
    profiles.value = []
    showToast(e.message || 'Chargement profils impossible.')
  } finally {
    loadingList.value = false
  }
}

function scheduleSearch() {
  loadingList.value = true
  clearTimeout(searchTimer)
  searchTimer = setTimeout(loadProfiles, 300)
}

async function openProfile(id, { silent = false } = {}) {
  if (loadingProfile.value) return
  loadingProfile.value = true
  try {
    const data = await fetchProfile(id, { english: english.value })
    selectedId.value = data.id
    cvMarkdown.value = data.markdown || ''
    exportFilename.value = data.filename || 'cv'
    if (!silent) showToast(`Profil chargé : ${data.name}`)
  } catch (e) {
    showToast(e.message || 'Impossible de charger le profil.')
  } finally {
    loadingProfile.value = false
  }
}

async function loadDefault() {
  if (loadingProfile.value) return
  loadingProfile.value = true
  try {
    const data = await fetchDefaultProfile({ english: english.value })
    selectedId.value = data.id
    cvMarkdown.value = data.markdown || ''
    exportFilename.value = data.filename || 'cv-lucas-schrever-dotnet-react'
    showToast(`Profil défaut : ${data.name}`)
  } catch (e) {
    showToast(e.message || 'Pas de profil par défaut.')
  } finally {
    loadingProfile.value = false
  }
}

async function restoreSession() {
  if (selectedId.value && cvMarkdown.value.trim()) {
    const stillThere = profiles.value.some((p) => p.id === selectedId.value)
    if (!stillThere) {
      try {
        await fetchProfile(selectedId.value)
      } catch {
        selectedId.value = null
        cvMarkdown.value = ''
        exportFilename.value = 'cv'
        await loadDefault()
        return
      }
    }
    showToast('Session restaurée')
    return
  }
  if (selectedId.value) {
    await openProfile(selectedId.value, { silent: true })
    return
  }
  await loadDefault()
}

async function onDelete(profile) {
  if (profile.is_default) {
    showToast('Le profil par défaut ne peut pas être supprimé.')
    return
  }
  const ok = window.confirm(`Supprimer le profil « ${profile.name} » ?`)
  if (!ok) return
  try {
    await deleteProfile(profile.id)
    if (selectedId.value === profile.id) {
      selectedId.value = null
      cvMarkdown.value = ''
      exportFilename.value = 'cv'
    }
    showToast('Profil supprimé.')
    await loadProfiles()
  } catch (e) {
    showToast(e.message || 'Suppression impossible.')
  }
}

async function onAnalyze() {
  const text = jobText.value.trim()
  if (text.length < 10) {
    showToast('Colle une offre (min. 10 caractères).')
    return
  }
  analyzing.value = true
  adaptInfo.value = null
  exportNote.value = ''
  try {
    const result = await analyzeJob({
      job_text: text,
      profile_id: selectedId.value || undefined,
      english: english.value,
    })
    if (!result.profile) {
      adaptInfo.value = {
        status: 'error',
        message: result.message || 'Adaptation impossible.',
      }
      showToast(result.message || 'Adaptation impossible.')
      return
    }
    selectedId.value = result.profile.id
    cvMarkdown.value = result.profile.markdown || ''
    exportFilename.value = result.profile.filename || 'cv'
    adaptInfo.value = {
      status: 'ok',
      message: result.message || 'Profil adapté',
      reason: result.reason || '',
      source: result.source || '',
      fallback: Boolean(result.fallback),
      company: result.company || result.profile.company || '',
      matchedVia: result.matched_via || '',
      profileName: result.profile.name || '',
      title: result.profile.title || '',
      filename: result.profile.filename || '',
      addedSkills: result.added_skills || [],
      missingSkills: result.missing_skills || [],
    }
    showToast(result.message || 'Profil adapté')
  } catch (e) {
    adaptInfo.value = {
      status: 'error',
      message: e.message || 'Adaptation impossible.',
    }
    showToast(e.message || 'Adaptation impossible.')
  } finally {
    analyzing.value = false
  }
}

async function onExportPdf() {
  if (!cvMarkdown.value.trim()) {
    showToast('Rien à exporter.')
    return
  }
  pdfLoading.value = true
  try {
    normalizeFilename()
    const { blob, filename } = await exportPdf({
      markdown: cvMarkdown.value,
      filename: exportFilename.value,
    })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = filename
    a.click()
    URL.revokeObjectURL(a.href)
    showToast(`PDF téléchargé — ${filename}`)
    exportNote.value = filename
  } catch (e) {
    showToast(e.message || 'PDF indisponible.')
  } finally {
    pdfLoading.value = false
  }
}

watch(english, async (val, oldVal) => {
  if (val === oldVal) return
  persist()
  if (selectedId.value) {
    await openProfile(selectedId.value)
  }
})

watch(category, () => {
  loadingList.value = true
  loadProfiles()
})

watch([jobText, cvMarkdown, selectedId, exportFilename], () => {
  persist()
})

onMounted(async () => {
  try {
    await pingApi()
    await checkOllama()
    await loadCategories()
    await loadProfiles()
    await restoreSession()
  } catch (e) {
    showToast(e.message || 'Backend indisponible.')
  } finally {
    persistReady = true
    persist()
  }
})
</script>

<template>
  <div class="app-shell">
    <header class="topbar">
      <div class="brand">
        <div>
          <h1>CV Generator</h1>
          <p class="muted">Profils statiques → offre → adaptation → PDF</p>
        </div>
      </div>
      <div class="topbar-actions">
        <label class="checkbox" :class="{ disabled: loadingProfile }">
          <input v-model="english" type="checkbox" :disabled="loadingProfile || analyzing" />
          En anglais
        </label>
        <button
          type="button"
          class="btn-secondary"
          :disabled="loadingProfile"
          @click="loadDefault"
        >
          Profil défaut
        </button>
        <button
          type="button"
          class="ollama-pill"
          :class="`ollama-pill--${ollamaState}`"
          title="Cliquer pour revérifier"
          @click="checkOllama"
        >
          {{ ollamaStatus }}
        </button>
      </div>
    </header>

    <section class="panel panel-profiles">
      <div class="filters">
        <input
          v-model="search"
          class="search-input"
          type="search"
          placeholder="Rechercher un profil…"
          :disabled="loadingProfile"
          @input="scheduleSearch"
        />
        <select
          v-model="category"
          class="category-select"
          :disabled="loadingProfile"
        >
          <option value="">Toutes les catégories</option>
          <option v-for="c in categories" :key="c.id" :value="c.name">
            {{ c.label_fr }}
          </option>
        </select>
      </div>

      <div v-if="loadingList" class="inline-loader">
        <span class="spinner" />
        <span>Recherche…</span>
      </div>

      <ul v-if="profiles.length" class="profile-list" :class="{ dimmed: loadingList }">
        <li
          v-for="p in profiles"
          :key="p.id"
          :class="{ active: selectedId === p.id, default: p.is_default }"
        >
          <button
            type="button"
            class="profile-open"
            :disabled="loadingProfile"
            @click="openProfile(p.id)"
          >
            <span class="profile-name">
              {{ p.name }}
              <span v-if="p.is_default" class="badge">défaut</span>
            </span>
            <span class="profile-meta">{{ p.category?.label_fr }} · {{ p.title }}</span>
          </button>
          <button
            type="button"
            class="history-delete"
            title="Supprimer"
            :disabled="p.is_default || loadingProfile"
            @click="onDelete(p)"
          >
            ×
          </button>
        </li>
      </ul>
      <p v-else-if="loadingList" class="muted">Chargement…</p>
      <p v-else class="muted">Aucun profil.</p>
    </section>

    <div class="workspace">
      <section class="panel col-input">
        <div class="panel-head">
          <h2>Fiche de poste</h2>
        </div>
        <textarea
          v-model="jobText"
          class="editor-field"
          placeholder="Colle l’offre : intitulé, missions, stack…"
          :disabled="analyzing"
        />
      </section>

      <section class="panel col-preview">
        <div class="panel-head">
          <h2>CV</h2>
          <label class="filename-edit">
            <input
              v-model="exportFilename"
              class="filename-input"
              type="text"
              spellcheck="false"
              aria-label="Nom du fichier PDF"
              :disabled="loadingProfile || pdfLoading"
              @blur="normalizeFilename"
            />
            <span class="filename-ext">.pdf</span>
          </label>
        </div>
        <div class="cv-wrap" :class="{ loading: loadingProfile }">
          <div v-if="loadingProfile" class="cv-overlay">
            <span class="spinner spinner--dark" />
            <span>Chargement du profil…</span>
          </div>
          <textarea
            v-model="cvMarkdown"
            class="editor-field"
            spellcheck="false"
            placeholder="Markdown du CV…"
            :disabled="loadingProfile"
          />
        </div>
      </section>
    </div>

    <section class="panel panel-actions">
      <div class="panel-head">
        <h2>Adaptation</h2>
      </div>
      <div class="actions-row">
        <button
          class="btn-action btn-action--adapt"
          type="button"
          :disabled="analyzing"
          @click="onAnalyze"
        >
          {{
            analyzing
              ? (ollamaReady ? 'Adaptation Ollama…' : 'Adaptation…')
              : 'Adapter le profil à l’offre'
          }}
        </button>
        <button
          class="btn-action btn-action--export"
          type="button"
          :disabled="pdfLoading || loadingProfile || !cvMarkdown.trim()"
          @click="onExportPdf"
        >
          {{ pdfLoading ? 'Export…' : 'Télécharger PDF' }}
        </button>
      </div>
      <div v-if="analyzing || pdfLoading" class="inline-loader">
        <span class="spinner" />
        <span>
          {{
            analyzing
              ? (ollamaReady ? 'Adaptation Ollama…' : 'Adaptation locale…')
              : 'Export PDF…'
          }}
        </span>
      </div>
      <dl v-if="adaptInfo && !analyzing" class="adapt-meta" :class="{ error: adaptInfo.status === 'error' }">
        <div v-if="adaptInfo.message">
          <dt>Résultat</dt>
          <dd>{{ adaptInfo.message }}</dd>
        </div>
        <div v-if="adaptInfo.profileName">
          <dt>Profil</dt>
          <dd>{{ adaptInfo.profileName }}</dd>
        </div>
        <div v-if="adaptInfo.title">
          <dt>Titre</dt>
          <dd>{{ adaptInfo.title }}</dd>
        </div>
        <div v-if="adaptInfo.company">
          <dt>Entreprise</dt>
          <dd>{{ adaptInfo.company }}</dd>
        </div>
        <div v-if="adaptInfo.source">
          <dt>Source</dt>
          <dd>
            {{ adaptInfo.source }}
            <span v-if="adaptInfo.fallback" class="badge-warn">fallback</span>
          </dd>
        </div>
        <div v-if="adaptInfo.matchedVia">
          <dt>Matching</dt>
          <dd>
            {{
              adaptInfo.matchedVia === 'ollama'
                ? 'matching Ollama'
                : adaptInfo.matchedVia === 'closest'
                  ? 'profil le plus proche (mots-clés)'
                  : 'profil sélectionné'
            }}
          </dd>
        </div>
        <div v-if="adaptInfo.reason">
          <dt>Détail</dt>
          <dd>{{ adaptInfo.reason }}</dd>
        </div>
        <div v-if="adaptInfo.addedSkills?.length">
          <dt>Compétences mises en avant</dt>
          <dd>{{ adaptInfo.addedSkills.join(', ') }}</dd>
        </div>
        <div v-if="adaptInfo.missingSkills?.length">
          <dt>Dans l’offre, hors profil</dt>
          <dd>{{ adaptInfo.missingSkills.join(', ') }}</dd>
        </div>
        <div v-if="adaptInfo.filename">
          <dt>Fichier</dt>
          <dd>{{ adaptInfo.filename }}.pdf</dd>
        </div>
      </dl>
      <p v-else-if="!analyzing && !pdfLoading && !adaptInfo" class="muted adapt-placeholder">
        Lance une adaptation pour voir le matching, le titre, l’entreprise et la source ici.
      </p>
      <p v-if="exportNote && !pdfLoading" class="muted export-note">
        Dernier PDF : <strong>{{ exportNote }}</strong>
      </p>
    </section>

    <div v-if="toast" class="toast">{{ toast }}</div>
  </div>
</template>
