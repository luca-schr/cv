<script setup>
import { useCvApp } from "./composables/useCvApp.js";

const {
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
  hasMarkdown,
  progressSteps,
  stepState,
  generate,
  onProfileSelect,
  onFilenameInput,
  openGeneration,
  deleteGeneration,
  purgeHistory,
  downloadPdf,
  loadHistory,
} = useCvApp();

const profileStatusLabel = {
  loading: "Chargement du profil",
  ok: "Profil chargé",
  error: "Échec du chargement du profil",
};
</script>

<template>
  <div class="app-shell">
    <header class="topbar">
      <div class="brand">
        <img src="/favicon.ico" alt="" class="brand-logo" width="32" height="32" />
        <div>
          <h1>CV Generator</h1>
        </div>
      </div>
      <div class="topbar-meta">
        <span class="llm-pill" :class="llmOk ? 'ok' : 'warn'">{{ llmLabel }}</span>
      </div>
    </header>

    <section class="panel section-profiles">
      <div class="profile-bar">
        <h2>1. {{ headingTitle }}</h2>
        <div class="profile-select-wrap">
          <span
            class="status-dot"
            :class="profileStatus"
            :title="profileStatusLabel[profileStatus]"
            :aria-label="profileStatusLabel[profileStatus]"
          ></span>
          <select
            id="profile-select"
            class="profile-select"
            v-model.number="selectedProfileId"
            :disabled="isBusy"
            @change="onProfileSelect"
          >
            <option v-for="p in profiles" :key="p.id" :value="p.id">
              {{ p.name }}
            </option>
          </select>
        </div>
      </div>
    </section>

    <div class="editors-grid">
      <section class="panel editor-card">
        <h2 class="editor-col-title">2. Offre d'emploi</h2>
        <textarea
          v-model="jobText"
          class="editor-field"
          rows="14"
          :disabled="isBusy"
          placeholder="Colle l'offre (intitulé, employeur, missions, stack…)"
        ></textarea>
        <div class="options-row">
          <label class="checkbox">
            <input v-model="useLlm" type="checkbox" :disabled="!llmOk || isBusy" />
            LLM
          </label>
          <label class="checkbox">
            <input v-model="english" type="checkbox" :disabled="isBusy" />
            En anglais
          </label>
        </div>
        <button type="button" class="btn-generate" :disabled="isBusy" @click="generate">
          {{ generating ? "Adaptation en cours…" : "Adapter le CV" }}
        </button>
      </section>

      <section class="panel editor-card">
        <div class="editor-col-head">
          <h2 class="editor-col-title">Markdown rendu</h2>
          <label class="filename-field">
            <span class="sr-only">Nom du fichier</span>
            <input
              v-model="filename"
              class="filename-input"
              spellcheck="false"
              placeholder="lucas-schrever-…"
              @input="onFilenameInput"
            />
          </label>
        </div>
        <textarea
          v-model="markdown"
          class="editor-field preview"
          :class="{ 'mode-adapted': result }"
          rows="14"
          spellcheck="false"
          :disabled="isBusy"
          placeholder="Markdown du CV - modifiable avant export…"
        ></textarea>
        <button type="button" class="btn-export" :disabled="!hasMarkdown || isBusy" @click="downloadPdf">
          Exporter le PDF
        </button>
      </section>
    </div>

    <section class="panel section-loader" aria-live="polite">
      <div class="panel-head">
        <h2>Chargement</h2>
      </div>
      <div class="gen-progress">
        <div class="gen-progress-head">
          <span>{{ isBusy ? progressLabel : "Prêt" }}</span>
          <strong>{{ generating ? Math.round(progressPct) + "%" : isBusy ? "…" : "-" }}</strong>
        </div>
        <div
          class="gen-progress-track"
          role="progressbar"
          aria-valuemin="0"
          aria-valuemax="100"
          :aria-valuenow="generating ? Math.round(progressPct) : isBusy ? undefined : 0"
          :aria-busy="isBusy"
        >
          <div
            class="gen-progress-bar"
            :class="{ idle: !isBusy, indeterminate: isBusy && !generating }"
            :style="{ width: (generating ? Math.round(progressPct) : 0) + '%' }"
          ></div>
        </div>
        <ol class="gen-steps">
          <li v-for="step in progressSteps" :key="step.id" :class="stepState(step.id)">
            {{ step.label }}
          </li>
        </ol>
      </div>
      <ul v-if="result?.warnings?.length" class="warnings">
        <li v-for="(w, i) in result.warnings" :key="i">{{ w }}</li>
      </ul>
      <div v-if="result?.match" class="match-panel">
        <div class="match-head">
          <h3>Match offre / CV</h3>
          <strong>{{ Math.round((result.match.score || 0) * 100) }}%</strong>
        </div>
        <p class="muted match-hint">
          Compétences de l'offre présentes dans le profil vs absentes (non inventées par le LLM).
        </p>
        <div class="match-tags" v-if="result.match.matched?.length">
          <span class="match-label">Couvertes</span>
          <span v-for="tag in result.match.matched" :key="'m-' + tag" class="tag ok">{{ tag }}</span>
        </div>
        <div class="match-tags" v-if="result.match.emphasize?.length">
          <span class="match-label">À mettre en avant</span>
          <span v-for="tag in result.match.emphasize" :key="'e-' + tag" class="tag accent">{{ tag }}</span>
        </div>
        <div class="match-tags" v-if="result.match.gaps?.length">
          <span class="match-label">Absentes du profil</span>
          <span v-for="tag in result.match.gaps" :key="'g-' + tag" class="tag gap">{{ tag }}</span>
        </div>
      </div>
    </section>

    <section class="panel section-history">
      <div class="panel-head spread">
        <h2>Historique</h2>
        <div class="row">
          <button type="button" class="secondary small danger-text" :disabled="isBusy" @click="purgeHistory">
            Vider
          </button>
          <button type="button" class="secondary small" :disabled="isBusy" @click="loadHistory">Rafraîchir</button>
        </div>
      </div>
      <ul class="history">
        <li v-if="!history.length" class="muted">Aucune génération.</li>
        <li v-for="g in history" :key="g.id">
          <div class="history-main">
            <button type="button" class="history-open" :disabled="isBusy" @click="openGeneration(g.id)">
              {{ g.title }}
            </button>
            <div class="date">{{ new Date(g.created_at).toLocaleString("fr-FR") }}</div>
          </div>
          <div class="history-actions">
            <button
              type="button"
              class="btn-icon danger"
              title="Supprimer"
              :disabled="isBusy"
              @click="deleteGeneration(g.id)"
            >
              ✕
            </button>
          </div>
        </li>
      </ul>
    </section>

    <div v-if="toastMsg" class="toast">{{ toastMsg }}</div>
  </div>
</template>
