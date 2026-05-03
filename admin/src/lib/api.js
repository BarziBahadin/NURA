export const API_BASE = import.meta.env.VITE_NURA_API_BASE || '/v1'

export function getToken() {
  return localStorage.getItem('nura_admin_token') || ''
}

export function setToken(token) {
  if (token) {
    localStorage.setItem('nura_admin_token', token)
  } else {
    localStorage.removeItem('nura_admin_token')
  }
}

// Client-side only: parse and check expiry. Does NOT verify HMAC signature.
// The server re-validates the signature on every authenticated request.
export function parseToken(token) {
  if (!token || !token.includes('.')) return null
  try {
    const [body] = token.split('.')
    const pad = body + '='.repeat((4 - (body.length % 4)) % 4)
    return JSON.parse(atob(pad))
  } catch {
    return null
  }
}

export function isTokenValid(token) {
  const payload = parseToken(token)
  if (!payload) return false
  return (payload.exp || 0) > Math.floor(Date.now() / 1000)
}

export function authHeaders() {
  const token = getToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export function getRole() {
  const p = parseToken(getToken())
  return p?.role || ''
}

export function getUsername() {
  const p = parseToken(getToken())
  return p?.sub || ''
}
