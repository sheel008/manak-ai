/**
 * Centralized API client for MANAK-AI FastAPI backend.
 * Provides unified request configuration, headers, and robust error handling.
 */

const getApiBase = () => {
  const target = import.meta.env.VITE_API_TARGET || import.meta.env.VITE_API_URL
  if (target) {
    const trimmed = target.trim().replace(/\/+$/, '')
    if (trimmed.startsWith('http://') || trimmed.startsWith('https://')) {
      return trimmed.endsWith('/api') ? trimmed : `${trimmed}/api`
    }
    return trimmed.startsWith('/') ? trimmed : `/${trimmed}`
  }
  return '/api'
}

export const API_BASE = getApiBase()

async function apiFetch(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`
  const headers = { ...options.headers }

  // Automatically set Content-Type to JSON if body is a plain object and not FormData
  if (options.body && !(options.body instanceof FormData) && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json'
    options.body = typeof options.body === 'string' ? options.body : JSON.stringify(options.body)
  }

  const res = await fetch(url, { ...options, headers })

  if (!res.ok) {
    let errorDetail = `Request failed with status ${res.status}`
    try {
      const errData = await res.json()
      errorDetail = errData.detail || errData.error || errData.message || errorDetail
    } catch {
      try {
        const text = await res.text()
        if (text) errorDetail = text
      } catch {
        // use default status error
      }
    }
    const err = new Error(errorDetail)
    err.status = res.status
    throw err
  }

  // Handle plain text or blob responses when requested
  if (options.responseType === 'text') {
    return res.text()
  }
  if (options.responseType === 'blob') {
    return res.blob()
  }

  return res.json()
}

export const api = {
  search: (query, department = null, reopen = false, extra = {}) => {
    const payload = { query, reopen, ...extra };
    if (department) payload.department = department;
    return apiFetch('/search', {
      method: 'POST',
      body: payload,
    });
  },

  searchDocument: (file, department = null) => {
    const formData = new FormData()
    formData.append('document', file)
    if (department) {
      formData.append('department', department)
    }
    return apiFetch('/search/document', {
      method: 'POST',
      body: formData,
    })
  },

  // ── Standards ──
  getStandard: (isNumber) =>
    apiFetch(`/standards/${encodeURIComponent(isNumber)}`),

  compareStandards: (isNumbers) =>
    apiFetch('/standards/compare', {
      method: 'POST',
      body: { is_numbers: isNumbers },
    }),

  getRelatedStandards: (isNumber, limit = 12) =>
    apiFetch(`/standards/${encodeURIComponent(isNumber)}/related?limit=${limit}`),

  // ── QCO & Certification ──
  checkQCO: (productName) =>
    apiFetch('/certification-check', {
      method: 'POST',
      body: { product_name: productName },
    }),

  listQCO: () =>
    apiFetch('/qco/list'),

  // ── History & Saved ──
  getHistory: (department = null) => {
    const query = department ? `?department=${encodeURIComponent(department)}` : ''
    return apiFetch(`/history${query}`)
  },

  getSaved: () =>
    apiFetch('/saved'),

  saveStandard: (isNumber) =>
    apiFetch('/saved', {
      method: 'POST',
      body: { is_number: isNumber },
    }),

  deleteSaved: (isNumber) =>
    apiFetch(`/saved/${encodeURIComponent(isNumber)}`, {
      method: 'DELETE',
    }),

  // ── Dashboard ──
  getDashboardStats: () =>
    apiFetch('/dashboard/stats'),

  getDashboardTrends: () =>
    apiFetch('/dashboard/trends'),

  getDepartments: () =>
    apiFetch('/departments'),

  // ── Reviews ──
  submitReview: (requestId, isNumber, decision) =>
    apiFetch('/reviews', {
      method: 'POST',
      body: { request_id: requestId, is_number: isNumber, decision },
    }),

  getReviews: (requestId) =>
    apiFetch(`/reviews/${encodeURIComponent(requestId)}`),

  // ── Exports ──
  exportStandard: (isNumber) =>
    apiFetch(`/export/${encodeURIComponent(isNumber)}`, {
      method: 'POST',
      responseType: 'blob',
    }),

  exportGemPayload: (isNumber) =>
    apiFetch(`/export/gem-payload/${encodeURIComponent(isNumber)}`, {
      method: 'POST',
      responseType: 'blob',
    }),

  exportRequestReviewBlock: (requestId) =>
    apiFetch(`/export/${encodeURIComponent(requestId)}`, {
      method: 'POST',
      responseType: 'text',
    }),

  // ── Chat ──
  sendChatMessage: (message, sessionId = '', history = [], lang = 'en') =>
    apiFetch('/chat', {
      method: 'POST',
      body: { message, sessionId, history, lang },
    }),

  // ── Health Check ──
  checkHealth: () =>
    apiFetch('/health'),
}

export default api
