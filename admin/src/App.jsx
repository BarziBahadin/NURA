import React, { useState, useEffect } from 'react'
import { Routes, Route, Link, useLocation, useNavigate } from 'react-router-dom'
import Dashboard from './pages/Dashboard.jsx'
import LiveQueue from './pages/LiveQueue.jsx'
import SessionViewer from './pages/SessionViewer.jsx'
import KnowledgeBase from './pages/KnowledgeBase.jsx'
import Reports from './pages/Reports.jsx'
import Login from './pages/Login.jsx'
import UserManagement from './pages/UserManagement.jsx'
import SystemMonitor from './pages/SystemMonitor.jsx'
import { API_BASE, getToken, setToken, isTokenValid, getRole } from './lib/api.js'

// api.key is a live getter so every fetch call reads the current stored token.
// nginx injects the real API key for /v1/ routes, so backend auth always works.
// The JWT is used for: (a) showing/hiding the login page, (b) role-based nav.
export const api = {
  base: API_BASE,
  get key() { return getToken() },
}

const ALL_NAV_ITEMS = [
  { path: '/',          label: 'Dashboard',      icon: '📊', roles: ['admin', 'viewer'] },
  { path: '/queue',     label: 'Live Queue',      icon: '🔔', roles: ['admin', 'agent'] },
  { path: '/sessions',  label: 'Sessions',        icon: '💬', roles: ['admin', 'agent', 'viewer'] },
  { path: '/reports',   label: 'Reports',         icon: '📈', roles: ['admin', 'viewer'] },
  { path: '/knowledge', label: 'Knowledge Base',  icon: '📚', roles: ['admin'] },
  { path: '/users',     label: 'Team',            icon: '👥', roles: ['admin'] },
  { path: '/monitor',   label: 'System Monitor',  icon: '🖥️', roles: ['admin'] },
]

function Sidebar({ pendingCount, onLogout, role }) {
  const { pathname } = useLocation()
  const navItems = ALL_NAV_ITEMS.filter(item => item.roles.includes(role))
  return (
    <aside className="w-56 bg-gray-900 text-white flex flex-col min-h-screen">
      <div className="p-5 border-b border-gray-700">
        <div className="text-lg font-bold text-blue-400">NURA Admin</div>
        <div className="text-xs text-gray-400 mt-1">Customer Support</div>
      </div>
      <nav className="flex-1 p-3">
        {navItems.map(({ path, label, icon }) => (
          <Link
            key={path}
            to={path}
            className={`flex items-center gap-3 px-4 py-3 rounded-xl mb-1 text-sm transition ${
              pathname === path
                ? 'bg-blue-600 text-white'
                : 'text-gray-300 hover:bg-gray-700'
            }`}
          >
            <span>{icon}</span>
            <span className="flex-1">{label}</span>
            {path === '/queue' && pendingCount > 0 && (
              <span className="bg-red-500 text-white text-xs font-bold px-1.5 py-0.5 rounded-full min-w-[20px] text-center">
                {pendingCount}
              </span>
            )}
          </Link>
        ))}
      </nav>
      <div className="p-4 border-t border-gray-700">
        <button
          onClick={onLogout}
          className="w-full text-xs text-gray-400 hover:text-white hover:bg-gray-700 px-3 py-2 rounded-lg transition text-left"
        >
          Sign out
        </button>
        <div className="text-xs text-gray-600 mt-2">NURA v1.0 • Customer Support</div>
      </div>
    </aside>
  )
}

export default function App() {
  const [authed, setAuthed] = useState(() => isTokenValid(getToken()))
  const [pendingCount, setPendingCount] = useState(0)
  const role = getRole()

  function handleLogin(token) {
    setToken(token)
    setAuthed(true)
  }

  function handleLogout() {
    setToken(null)
    setAuthed(false)
  }

  // Poll the queue badge. A 401 from the API means our JWT was revoked server-side.
  useEffect(() => {
    if (!authed) return
    async function fetchPending() {
      try {
        const res = await fetch(`${API_BASE}/queue`, {
          headers: { Authorization: `Bearer ${getToken()}` },
        })
        if (res.status === 401) {
          handleLogout()
          return
        }
        const data = await res.json()
        setPendingCount(data.pending || 0)
      } catch {}
    }
    fetchPending()
    const t = setInterval(fetchPending, 5000)
    return () => clearInterval(t)
  }, [authed])

  if (!authed) {
    return <Login onLogin={handleLogin} />
  }

  return (
    <div className="flex min-h-screen">
      <Sidebar pendingCount={pendingCount} onLogout={handleLogout} role={role} />
      <main className="flex-1 overflow-auto">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/queue" element={<LiveQueue />} />
          <Route path="/sessions" element={<SessionViewer />} />
          <Route path="/reports" element={<Reports />} />
          <Route path="/knowledge" element={<KnowledgeBase />} />
          <Route path="/users" element={<UserManagement />} />
          <Route path="/monitor" element={<SystemMonitor />} />
        </Routes>
      </main>
    </div>
  )
}
