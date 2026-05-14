import { API_BASE, authHeaders, setToken } from './api.js'

let unauthorizedHandler = null

export function setUnauthorizedHandler(handler) {
  unauthorizedHandler = handler
}

export class ApiError extends Error {
  constructor(message, status, data) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.data = data
  }
}

export async function apiFetch(path, options = {}) {
  const url = path.startsWith('http') ? path : `${API_BASE}${path}`
  const headers = {
    ...authHeaders(),
    ...(options.body && !(options.body instanceof FormData) ? { 'Content-Type': 'application/json' } : {}),
    ...(options.headers || {}),
  }

  let response
  try {
    response = await fetch(url, { ...options, headers })
  } catch {
    throw new ApiError('Connection error. Check that the API is running.', 0, null)
  }

  if (response.status === 401) {
    setToken(null)
    unauthorizedHandler?.()
  }

  const text = await response.text()
  let data = null
  if (text) {
    try {
      data = JSON.parse(text)
    } catch {
      data = text
    }
  }

  if (!response.ok) {
    const detail = typeof data === 'object' && data ? data.detail || data.message : ''
    throw new ApiError(detail || `Request failed (${response.status})`, response.status, data)
  }

  return data
}

export const apiGet = path => apiFetch(path)
export const apiPost = (path, body, options = {}) => apiFetch(path, { method: 'POST', body: body instanceof FormData ? body : JSON.stringify(body ?? {}), ...options })
export const apiPatch = (path, body) => apiFetch(path, { method: 'PATCH', body: JSON.stringify(body ?? {}) })
export const apiDelete = path => apiFetch(path, { method: 'DELETE' })
