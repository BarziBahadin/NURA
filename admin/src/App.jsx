import React, { useState, useEffect } from 'react'
import { Routes, Route, Link, useLocation } from 'react-router-dom'
import {
  ChartBar, Bell, Folder, Lightbulb, ChatCircle, TrendUp,
  PuzzlePiece, ChatCenteredText, Books, Users, Monitor,
  CaretLeft, CaretRight, SignOut,
} from '@phosphor-icons/react'
import Dashboard from './pages/Dashboard.jsx'
import LiveQueue from './pages/LiveQueue.jsx'
import SessionViewer from './pages/SessionViewer.jsx'
import KnowledgeBase from './pages/KnowledgeBase.jsx'
import Reports from './pages/Reports.jsx'
import Cases from './pages/Cases.jsx'
import Suggestions from './pages/Suggestions.jsx'
import Login from './pages/Login.jsx'
import UserManagement from './pages/UserManagement.jsx'
import SystemMonitor from './pages/SystemMonitor.jsx'
import KnowledgeGapQueue from './pages/KnowledgeGapQueue.jsx'
import CannedReplies from './pages/CannedReplies.jsx'
import { API_BASE, getToken, setToken, isTokenValid, getRole } from './lib/api.js'

// api.key is a live getter so every fetch call reads the current stored token.
// The JWT is used for authenticated API calls, showing/hiding the login page,
// and role-based navigation.
export const api = {
  base: API_BASE,
  get key() { return getToken() },
}

const ALL_NAV_ITEMS = [
  { path: '/',               label: 'Dashboard',      Icon: ChartBar,         roles: ['admin', 'viewer'] },
  { path: '/queue',          label: 'Live Queue',      Icon: Bell,             roles: ['admin', 'agent'] },
  { path: '/cases',          label: 'Cases',           Icon: Folder,           roles: ['admin', 'agent', 'viewer'] },
  { path: '/suggestions',    label: 'Suggestions',     Icon: Lightbulb,        roles: ['admin', 'agent', 'viewer'] },
  { path: '/sessions',       label: 'Sessions',        Icon: ChatCircle,       roles: ['admin', 'agent', 'viewer'] },
  { path: '/reports',        label: 'Reports',         Icon: TrendUp,          roles: ['admin', 'viewer'] },
  { path: '/gaps',           label: 'Knowledge Gaps',  Icon: PuzzlePiece,      roles: ['admin'] },
  { path: '/canned-replies', label: 'Canned Replies',  Icon: ChatCenteredText, roles: ['admin'] },
  { path: '/knowledge',      label: 'Knowledge Base',  Icon: Books,            roles: ['admin'] },
  { path: '/users',          label: 'Team',            Icon: Users,            roles: ['admin'] },
  { path: '/monitor',        label: 'System Monitor',  Icon: Monitor,          roles: ['admin'] },
]

function AiToggle({ role, collapsed = false }) {
  const [enabled, setEnabled] = React.useState(null)

  React.useEffect(() => {
    async function fetchStatus() {
      try {
        const res = await fetch(`${API_BASE}/ai/status`, {
          headers: { Authorization: `Bearer ${getToken()}` },
        })
        const data = await res.json()
        setEnabled(data.openai_enabled ?? data.ai_enabled)
      } catch {}
    }
    fetchStatus()
    const t = setInterval(fetchStatus, 10000)
    return () => clearInterval(t)
  }, [])

  if (!['admin', 'agent'].includes(role)) return null

  async function toggle() {
    if (enabled === null) return
    const endpoint = enabled ? 'disable' : 'enable'
    try {
      const res = await fetch(`${API_BASE}/ai/${endpoint}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${getToken()}` },
      })
      const data = await res.json()
      setEnabled(data.openai_enabled ?? data.ai_enabled)
    } catch {}
  }

  return collapsed ? (
    <button
      onClick={toggle}
      disabled={role !== 'admin'}
      className={`w-10 h-10 mx-auto flex items-center justify-center rounded-xl text-[11px] font-bold transition relative ${
        enabled
          ? 'bg-green-900/60 text-green-300 hover:bg-green-900'
          : 'bg-red-900/60 text-red-300 hover:bg-red-900'
      } disabled:cursor-default`}
      title={role !== 'admin' ? 'OpenAI control is admin only' : (enabled ? 'OpenAI replies on' : 'OpenAI replies off')}
      aria-label={enabled ? 'OpenAI replies on' : 'OpenAI replies off'}
    >
      AI
      <span className={`absolute top-2 right-2 w-2 h-2 rounded-full ${enabled ? 'bg-green-400' : 'bg-red-400'}`} />
    </button>
  ) : (
    <div className="mb-2">
      <button
        onClick={toggle}
        disabled={role !== 'admin'}
        className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-semibold transition ${
          enabled
            ? 'bg-green-900/60 text-green-300 hover:bg-green-900'
            : 'bg-red-900/60 text-red-300 hover:bg-red-900'
        } disabled:cursor-default`}
        title={role !== 'admin' ? 'Admin only' : (enabled ? 'Stop sending customer text to OpenAI' : 'Allow OpenAI replies')}
      >
        <span className={`w-2 h-2 rounded-full flex-shrink-0 ${enabled ? 'bg-green-400' : 'bg-red-400'}`} />
        OpenAI {enabled === null ? '…' : enabled ? 'Replies On' : 'Replies Off'}
        {role === 'admin' && <span className="ml-auto opacity-60 text-xs">{enabled ? 'ON' : 'OFF'}</span>}
      </button>
    </div>
  )
}

function Sidebar({ pendingCount, onLogout, role, collapsed, onToggleCollapsed }) {
  const { pathname } = useLocation()
  const navItems = ALL_NAV_ITEMS.filter(item => item.roles.includes(role))
  return (
    <aside className={`${collapsed ? 'w-16' : 'w-56'} bg-gray-900 text-white flex flex-col h-screen sticky top-0 flex-shrink-0 transition-all duration-200`}>
      <div className={`${collapsed ? 'p-3' : 'p-5'} border-b border-gray-700 flex-shrink-0`}>
        <div className={`flex items-center ${collapsed ? 'justify-center' : 'justify-between'} gap-2`}>
          {!collapsed && (
            <div className="min-w-0">
              <div className="text-lg font-bold text-blue-400">NURA Admin</div>
              <div className="text-xs text-gray-400 mt-1">Customer Support</div>
            </div>
          )}
          <button
            onClick={onToggleCollapsed}
            className="w-9 h-9 rounded-xl bg-gray-800 hover:bg-gray-700 text-gray-300 hover:text-white flex items-center justify-center transition"
            title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {collapsed ? <CaretRight size={18} /> : <CaretLeft size={18} />}
          </button>
        </div>
      </div>
      <nav className={`flex-1 min-h-0 overflow-y-auto ${collapsed ? 'p-2' : 'p-3'}`}>
        {navItems.map(({ path, label, Icon }) => (
          <Link
            key={path}
            to={path}
            title={collapsed ? label : undefined}
            aria-label={label}
            className={`relative flex items-center ${collapsed ? 'justify-center px-0 py-3' : 'gap-3 px-3 py-2.5'} rounded-xl mb-1 text-sm transition ${
              pathname === path
                ? 'bg-blue-600 text-white'
                : 'text-gray-300 hover:bg-gray-700'
            }`}
          >
            <Icon size={22} />
            {!collapsed && <span className="flex-1">{label}</span>}
            {path === '/queue' && pendingCount > 0 && !collapsed && (
              <span className="bg-red-500 text-white text-xs font-bold px-1.5 py-0.5 rounded-full min-w-[20px] text-center">
                {pendingCount}
              </span>
            )}
            {path === '/queue' && pendingCount > 0 && collapsed && (
              <span className="absolute top-1.5 right-1.5 bg-red-500 text-white text-[10px] font-bold rounded-full min-w-[16px] h-4 px-1 flex items-center justify-center">
                {pendingCount > 9 ? '9+' : pendingCount}
              </span>
            )}
          </Link>
        ))}
      </nav>
      <div className={`${collapsed ? 'p-2' : 'p-4'} border-t border-gray-700 flex-shrink-0 bg-gray-900`}>
        <AiToggle role={role} collapsed={collapsed} />
        <button
          onClick={onLogout}
          className={`w-full text-xs text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg transition ${
            collapsed ? 'mt-2 h-10 flex items-center justify-center' : 'px-3 py-2 text-left'
          }`}
          title="Sign out"
          aria-label="Sign out"
        >
          {collapsed ? <SignOut size={20} /> : 'Sign out'}
        </button>
        {!collapsed && <div className="text-xs text-gray-600 mt-2">NURA v1.0 • Customer Support</div>}
      </div>
    </aside>
  )
}

export default function App() {
  const [authed, setAuthed] = useState(() => isTokenValid(getToken()))
  const [pendingCount, setPendingCount] = useState(0)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => localStorage.getItem('nura_sidebar_collapsed') === 'true')
  const role = getRole()

  function handleLogin(token) {
    setToken(token)
    setAuthed(true)
  }

  function handleLogout() {
    setToken(null)
    setAuthed(false)
  }

  function toggleSidebar() {
    setSidebarCollapsed(value => {
      const next = !value
      localStorage.setItem('nura_sidebar_collapsed', String(next))
      return next
    })
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
      <Sidebar
        pendingCount={pendingCount}
        onLogout={handleLogout}
        role={role}
        collapsed={sidebarCollapsed}
        onToggleCollapsed={toggleSidebar}
      />
      <main className="flex-1 overflow-auto">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/queue" element={<LiveQueue />} />
          <Route path="/cases" element={<Cases />} />
          <Route path="/suggestions" element={<Suggestions />} />
          <Route path="/sessions" element={<SessionViewer />} />
          <Route path="/reports" element={<Reports />} />
          <Route path="/gaps" element={<KnowledgeGapQueue />} />
          <Route path="/canned-replies" element={<CannedReplies />} />
          <Route path="/knowledge" element={<KnowledgeBase />} />
          <Route path="/users" element={<UserManagement />} />
          <Route path="/monitor" element={<SystemMonitor />} />
        </Routes>
      </main>
    </div>
  )
}
