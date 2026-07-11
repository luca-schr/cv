const API = '/api'

async function fetchApi(path, { method = 'GET', body, timeoutMs = 15000 } = {}) {
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
      throw new Error('Délai dépassé — le serveur met trop de temps à répondre.')
    }
    throw new Error('API indisponible — lance uvicorn dans server/ (port 8000).')
  } finally {
    clearTimeout(timer)
  }
}

async function consumeSse(response, onEvent) {
  if (!response.ok) {
    let detail = `Erreur ${response.status}`
    try {
      const data = await response.json()
      detail = data.detail || detail
    } catch {
      detail = await response.text()
    }
    throw new Error(detail)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let lastEvent = null

  function parseBuffer() {
    const parts = buffer.split('\n\n')
    buffer = parts.pop() || ''
    for (const block of parts) {
      const line = block.split('\n').find((l) => l.startsWith('data: '))
      if (!line) continue
      const event = JSON.parse(line.slice(6))
      lastEvent = event
      onEvent(event)
      if (event.type === 'error') {
        throw new Error(event.message || 'Erreur serveur')
      }
    }
  }

  while (true) {
    const { done, value } = await reader.read()
    if (value) {
      buffer += decoder.decode(value, { stream: true })
      parseBuffer()
    }
    if (done) {
      if (buffer.trim()) parseBuffer()
      break
    }
  }

  if (lastEvent?.type === 'complete') {
    return lastEvent
  }
  throw new Error('Flux interrompu avant la fin.')
}

export async function apiGet(path, options = {}) {
  const res = await fetchApi(path, options)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function apiPost(path, body, options = {}) {
  const res = await fetchApi(path, { ...options, method: 'POST', body })
  if (!res.ok) {
    let detail = `Erreur ${res.status}`
    try {
      const data = await res.json()
      detail = data.detail || detail
    } catch {
      /* ignore */
    }
    throw new Error(detail)
  }
  return res
}

export async function generateCvStream(payload, onProgress) {
  const res = await fetch(`${API}/generate/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  const finalEvent = await consumeSse(res, (event) => {
    if (event.type === 'progress' && onProgress) {
      onProgress(event)
    }
  })
  return finalEvent.result
}

export async function generateCv(payload) {
  const res = await apiPost('/generate', payload, { timeoutMs: 600000 })
  return res.json()
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

/** Attend une nouvelle génération (le serveur peut finir après coupure SSE). */
export async function waitForNewGeneration(beforeId, { attempts = 45, delayMs = 2000 } = {}) {
  for (let i = 0; i < attempts; i += 1) {
    try {
      const items = await fetchGenerations()
      const newest = items[0]
      if (newest?.id > beforeId) {
        return fetchGeneration(newest.id)
      }
    } catch {
      /* serveur occupé — réessayer */
    }
    await sleep(delayMs)
  }
  return null
}

export async function exportPdfStream(body, onProgress) {
  const res = await fetch(`${API}/export/pdf/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  const finalEvent = await consumeSse(res, (event) => {
    if (event.type === 'progress' && onProgress) {
      onProgress(event)
    }
  })
  const bytes = Uint8Array.from(atob(finalEvent.pdf_base64), (c) => c.charCodeAt(0))
  return {
    blob: new Blob([bytes], { type: 'application/pdf' }),
    filename: finalEvent.filename,
    pageCount: finalEvent.page_count,
  }
}

export async function fetchGenerations() {
  return apiGet('/generations', { timeoutMs: 8000 })
}

export async function fetchGeneration(id) {
  return apiGet(`/generations/${id}`, { timeoutMs: 15000 })
}

export async function fetchOllamaStatus() {
  return apiGet('/llm/status', { timeoutMs: 8000 })
}

export async function pingApi() {
  return apiGet('/ping', { timeoutMs: 5000 })
}

/** Réessaie une requête (utile au redémarrage du backend). */
export async function withRetry(fn, { attempts = 4, delayMs = 2000 } = {}) {
  let lastError
  for (let i = 0; i < attempts; i += 1) {
    try {
      return await fn()
    } catch (err) {
      lastError = err
      if (i < attempts - 1) {
        await new Promise((r) => setTimeout(r, delayMs))
      }
    }
  }
  throw lastError
}
