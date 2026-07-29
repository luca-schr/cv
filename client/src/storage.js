const KEY = 'cv-generator:ui-v1'

const DEFAULTS = {
  jobText: '',
  cvMarkdown: '',
  selectedId: null,
  exportFilename: 'cv',
  english: false,
}

export function loadUiState() {
  try {
    const raw = localStorage.getItem(KEY)
    if (!raw) return { ...DEFAULTS }
    const parsed = JSON.parse(raw)
    return {
      jobText: typeof parsed.jobText === 'string' ? parsed.jobText : '',
      cvMarkdown: typeof parsed.cvMarkdown === 'string' ? parsed.cvMarkdown : '',
      selectedId:
        Number.isFinite(Number(parsed.selectedId)) && Number(parsed.selectedId) > 0
          ? Number(parsed.selectedId)
          : null,
      exportFilename:
        typeof parsed.exportFilename === 'string' && parsed.exportFilename.trim()
          ? parsed.exportFilename.trim()
          : 'cv',
      english: Boolean(parsed.english),
    }
  } catch {
    return { ...DEFAULTS }
  }
}

export function saveUiState(partial) {
  try {
    const current = loadUiState()
    const next = { ...current, ...partial }
    localStorage.setItem(
      KEY,
      JSON.stringify({
        jobText: String(next.jobText || ''),
        cvMarkdown: String(next.cvMarkdown || ''),
        selectedId: next.selectedId == null ? null : Number(next.selectedId),
        exportFilename: String(next.exportFilename || 'cv'),
        english: Boolean(next.english),
      }),
    )
  } catch {
    /* quota / private mode */
  }
}
