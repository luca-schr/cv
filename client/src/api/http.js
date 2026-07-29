const API = '/api'

async function request(path, { method = 'GET', body, timeoutMs = 15000 } = {}) {
  const ctrl = new AbortController()
  const timer = setTimeout(() => ctrl.abort(), timeoutMs)
  try {
    const res = await fetch(`${API}${path}`, {
      method,
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
      signal: ctrl.signal,
    })
    return res
  } catch (err) {
    if (err.name === 'AbortError') {
      throw new Error('Délai dépassé — Ollama trop lent ou serveur indisponible.')
    }
    throw new Error('API indisponible — vérifie que le serveur Express tourne (port 8000).')
  } finally {
    clearTimeout(timer)
  }
}

async function readError(res) {
  try {
    const data = await res.json()
    return data.detail || `Erreur ${res.status}`
  } catch {
    return `Erreur ${res.status}`
  }
}

export async function pingApi() {
  const res = await request('/ping', { timeoutMs: 5000 })
  if (!res.ok) throw new Error(await readError(res))
  return res.json()
}

export async function fetchCategories() {
  const res = await request('/categories')
  if (!res.ok) throw new Error(await readError(res))
  return res.json()
}

export async function fetchProfiles({ q = '', category = '' } = {}) {
  const qs = new URLSearchParams()
  if (q) qs.set('q', q)
  if (category) qs.set('category', category)
  const res = await request(`/profiles?${qs}`)
  if (!res.ok) throw new Error(await readError(res))
  return res.json()
}

export async function fetchProfile(id, { english = false } = {}) {
  const res = await request(`/profiles/${id}`)
  if (!res.ok) throw new Error(await readError(res))
  const data = await res.json()
  if (english && data.markdown_en) {
    return {
      ...data,
      markdown: data.markdown_en,
      title: data.title_en || data.title,
      summary: data.summary_en || data.summary,
    }
  }
  return data
}

export async function fetchDefaultProfile({ english = false } = {}) {
  const res = await request('/profiles/default')
  if (!res.ok) throw new Error(await readError(res))
  const data = await res.json()
  if (english && data.markdown_en) {
    return {
      ...data,
      markdown: data.markdown_en,
      title: data.title_en || data.title,
      summary: data.summary_en || data.summary,
    }
  }
  return data
}

export async function deleteProfile(id) {
  const res = await request(`/profiles/${id}`, { method: 'DELETE' })
  if (!res.ok) throw new Error(await readError(res))
}

export async function analyzeJob({ job_text, profile_id, english = false }) {
  const res = await request('/analyze', {
    method: 'POST',
    body: { job_text, profile_id, english },
    timeoutMs: 180000,
  })
  if (!res.ok) throw new Error(await readError(res))
  return res.json()
}

export async function fetchOllamaStatus() {
  const res = await request('/llm/status', { timeoutMs: 8000 })
  if (!res.ok) throw new Error(await readError(res))
  return res.json()
}

export async function exportPdf({ markdown, filename }) {
  const res = await request('/export/pdf', {
    method: 'POST',
    body: { markdown, filename },
    timeoutMs: 120000,
  })
  if (!res.ok) throw new Error(await readError(res))
  const blob = await res.blob()
  const cd = res.headers.get('Content-Disposition') || ''
  const m = /filename="([^"]+)"/.exec(cd)
  return { blob, filename: m?.[1] || `${filename || 'cv'}.pdf` }
}
