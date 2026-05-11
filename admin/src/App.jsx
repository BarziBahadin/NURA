import React, { useState, useEffect } from 'react'
import { Routes, Route, Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import {
  ChartBar, Bell, PhoneCall, Folder, Lightbulb, ChatCircle, TrendUp,
  PuzzlePiece, ChatCenteredText, Books, Users, Monitor, Tree,
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
import Rules from './pages/Rules.jsx'
import { API_BASE, getToken, setToken, isTokenValid, getRole, getUsername, parseToken } from './lib/api.js'

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
  { path: '/calls',          label: 'Calls',           Icon: PhoneCall,        roles: ['admin', 'agent'] },
  { path: '/cases',          label: 'Cases',           Icon: Folder,           roles: ['admin', 'agent', 'viewer'] },
  { path: '/suggestions',    label: 'Suggestions',     Icon: Lightbulb,        roles: ['admin', 'agent', 'viewer'] },
  { path: '/sessions',       label: 'Sessions',        Icon: ChatCircle,       roles: ['admin', 'agent', 'viewer'] },
  { path: '/reports',        label: 'Reports',         Icon: TrendUp,          roles: ['admin', 'viewer'] },
  { path: '/gaps',           label: 'Knowledge Gaps',  Icon: PuzzlePiece,      roles: ['admin'] },
  { path: '/canned-replies', label: 'Canned Replies',  Icon: ChatCenteredText, roles: ['admin'] },
  { path: '/knowledge',      label: 'Knowledge Base',  Icon: Books,            roles: ['admin'] },
  { path: '/rules',          label: 'Rules Engine',    Icon: Tree,             roles: ['admin'] },
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

  return (
    <div className={`mb-2 ${collapsed ? 'w-10 mx-auto' : 'w-full'}`}>
      <button
        onClick={toggle}
        disabled={role !== 'admin'}
        className={`h-10 grid items-center rounded-xl text-xs font-semibold transition-[background-color,color,box-shadow,transform] duration-200 overflow-hidden ${
          collapsed ? 'w-10 grid-cols-[40px] justify-center' : 'w-full grid-cols-[40px_1fr_auto]'
        } ${
          enabled
            ? 'bg-green-900/60 text-green-300 hover:bg-green-900'
            : 'bg-red-900/60 text-red-300 hover:bg-red-900'
        } disabled:cursor-default`}
        title={role !== 'admin' ? 'Admin only' : (enabled ? 'OpenAI replies on' : 'OpenAI replies off')}
        aria-label={enabled ? 'OpenAI replies on' : 'OpenAI replies off'}
      >
        <span className="flex items-center justify-center">
          <span className={`w-2 h-2 rounded-full ${enabled ? 'bg-green-400' : 'bg-red-400'}`} />
        </span>
        {!collapsed && (
          <>
            <span className="whitespace-nowrap overflow-hidden max-w-[132px] opacity-100 translate-x-0 transition-[max-width,opacity,transform] duration-500 ease-[cubic-bezier(0.22,1,0.36,1)]">
              OpenAI {enabled === null ? '…' : enabled ? 'Replies On' : 'Replies Off'}
            </span>
            {role === 'admin' && (
              <span className="mr-3 opacity-60 text-xs whitespace-nowrap overflow-hidden max-w-[28px]">
                {enabled ? 'ON' : 'OFF'}
              </span>
            )}
          </>
        )}
      </button>
    </div>
  )
}

function Sidebar({ pendingCount, callCount, onLogout, role, username, collapsed, onToggleCollapsed, onNavClick }) {
  const { pathname } = useLocation()
  const navItems = ALL_NAV_ITEMS.filter(item => item.roles.includes(role))
  const signedInLabel = username || role || 'User'
  return (
    <aside className="relative w-20 text-white h-screen sticky top-0 flex-shrink-0 overflow-visible z-30">
      <div className={`${collapsed ? 'w-20 shadow-none' : 'w-60 shadow-2xl shadow-gray-900/25'} absolute inset-y-0 left-0 bg-gray-900 flex flex-col transition-[width,box-shadow] duration-500 ease-[cubic-bezier(0.22,1,0.36,1)] will-change-[width] overflow-hidden`}>
      <div className="h-[78px] border-b border-gray-700 flex-shrink-0 px-3 flex items-center">
        {collapsed ? (
          <button
            onClick={onToggleCollapsed}
            className="w-10 h-10 mx-auto rounded-xl bg-gray-800 hover:bg-gray-700 text-gray-300 hover:text-white flex items-center justify-center transition-[background-color,color,transform] duration-200 ease-out hover:scale-[1.03]"
            title="Expand sidebar"
            aria-label="Expand sidebar"
          >
            <CaretRight size={18} />
          </button>
        ) : (
          <div className="grid w-full grid-cols-[40px_1fr_40px] items-center gap-2">
            <div className="w-10 h-10 rounded-xl bg-blue-600 text-white flex items-center justify-center text-sm font-black tracking-wide shadow-sm">
            N
            </div>
            <div className="min-w-0 overflow-hidden">
              <div className="text-lg font-bold text-blue-400 whitespace-nowrap leading-tight">NURA Admin</div>
              <div className="text-xs text-gray-400 mt-0.5 whitespace-nowrap truncate" title={signedInLabel}>
                {signedInLabel}
              </div>
            </div>
            <button
              onClick={onToggleCollapsed}
              className="w-10 h-10 rounded-xl bg-gray-800 hover:bg-gray-700 text-gray-300 hover:text-white flex items-center justify-center transition-[background-color,color,transform] duration-200 ease-out hover:scale-[1.03]"
              title="Collapse sidebar"
              aria-label="Collapse sidebar"
            >
              <CaretLeft size={18} />
            </button>
          </div>
        )}
      </div>
      <nav className={`flex-1 min-h-0 overflow-y-auto ${collapsed ? 'px-0 py-3 flex flex-col items-center' : 'p-3'}`}>
        {navItems.map(({ path, label, Icon }) => (
          <Link
            key={path}
            to={path}
            onClick={onNavClick}
            title={collapsed ? label : undefined}
            aria-label={label}
            className={`group relative grid items-center h-10 rounded-xl mb-2 text-sm overflow-hidden transition-[background-color,color,box-shadow,transform] duration-200 ease-out ${
              collapsed ? 'w-10 grid-cols-[40px]' : 'w-full grid-cols-[40px_1fr_auto]'
            } ${
              pathname === path
                ? 'bg-blue-600 text-white'
                : 'text-gray-300 hover:bg-gray-700'
            } ${collapsed ? 'justify-center' : ''}`}
          >
            <span className="w-10 h-10 flex items-center justify-center transition-transform duration-200 ease-out group-hover:scale-105">
              <Icon size={20} />
            </span>
            <span className={`whitespace-nowrap overflow-hidden transition-[max-width,opacity,transform] duration-500 ease-[cubic-bezier(0.22,1,0.36,1)] ${
              collapsed ? 'max-w-0 opacity-0 translate-x-3' : 'max-w-[150px] opacity-100 translate-x-0'
            }`}>
              {label}
            </span>
            {path === '/queue' && pendingCount > 0 && !collapsed && (
              <span className="mr-3 bg-red-500 text-white text-xs font-bold px-1.5 py-0.5 rounded-full min-w-[20px] text-center transition-all duration-300">
                {pendingCount}
              </span>
            )}
            {path === '/queue' && pendingCount > 0 && collapsed && (
              <span className="absolute top-1.5 right-1.5 bg-red-500 text-white text-[10px] font-bold rounded-full min-w-[16px] h-4 px-1 flex items-center justify-center">
                {pendingCount > 9 ? '9+' : pendingCount}
              </span>
            )}
            {path === '/calls' && callCount > 0 && !collapsed && (
              <span className="mr-3 bg-orange-500 text-white text-xs font-bold px-1.5 py-0.5 rounded-full min-w-[20px] text-center transition-all duration-300">
                {callCount}
              </span>
            )}
            {path === '/calls' && callCount > 0 && collapsed && (
              <span className="absolute top-1.5 right-1.5 bg-orange-500 text-white text-[10px] font-bold rounded-full min-w-[16px] h-4 px-1 flex items-center justify-center">
                {callCount > 9 ? '9+' : callCount}
              </span>
            )}
          </Link>
        ))}
      </nav>
      <div className={`${collapsed ? 'px-0 py-3' : 'p-3'} border-t border-gray-700 flex-shrink-0 bg-gray-900`}>
        <AiToggle role={role} collapsed={collapsed} />
        <button
          onClick={onLogout}
          className={`h-10 text-xs text-gray-400 hover:text-white hover:bg-gray-700 rounded-xl transition-[background-color,color,transform] duration-200 ease-out grid items-center overflow-hidden ${
            collapsed ? 'w-10 mx-auto grid-cols-[40px] justify-center' : 'w-full grid-cols-[40px_1fr]'
          }`}
          title="Sign out"
          aria-label="Sign out"
        >
          <span className="w-10 flex items-center justify-center">
            <SignOut size={20} />
          </span>
          {!collapsed && (
            <span className="whitespace-nowrap overflow-hidden text-left max-w-[90px] opacity-100 translate-x-0 transition-[max-width,opacity,transform] duration-500 ease-[cubic-bezier(0.22,1,0.36,1)]">
              Sign out
            </span>
          )}
        </button>
        <div className={`text-xs text-gray-600 mt-2 whitespace-nowrap overflow-hidden transition-[max-width,opacity,transform] duration-500 ease-[cubic-bezier(0.22,1,0.36,1)] ${
          collapsed ? 'max-w-0 opacity-0' : 'max-w-[180px] opacity-100'
        }`}>
          NURA v1.0 • Customer Support
        </div>
      </div>
      </div>
    </aside>
  )
}

export default function App() {
  const [authed, setAuthed] = useState(() => isTokenValid(getToken()))
  const [pendingCount, setPendingCount] = useState(0)
  const [callCount, setCallCount] = useState(0)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => localStorage.getItem('nura_sidebar_collapsed') === 'true')
  const [role, setRole] = useState(() => getRole())
  const [username, setUsername] = useState(() => getUsername())
  const navigate = useNavigate()

  function handleLogin(token) {
    setToken(token)
    const payload = parseToken(token) || {}
    setRole(payload.role || '')
    setUsername(payload.sub || '')
    setAuthed(true)
    navigate('/', { replace: true })
  }

  function handleLogout() {
    setToken(null)
    setRole('')
    setUsername('')
    setAuthed(false)
    navigate('/', { replace: true })
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

        const callsRes = await fetch(`${API_BASE}/voice/calls`, {
          headers: { Authorization: `Bearer ${getToken()}` },
        })
        if (callsRes.ok) {
          const callsData = await callsRes.json()
          setCallCount((callsData.calls || []).length)
        }
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
        callCount={callCount}
        onLogout={handleLogout}
        role={role}
        username={username}
        collapsed={sidebarCollapsed}
        onToggleCollapsed={toggleSidebar}
        onNavClick={() => {
          if (!sidebarCollapsed) {
            setSidebarCollapsed(true)
            localStorage.setItem('nura_sidebar_collapsed', 'true')
          }
        }}
      />
      <main className="flex-1 min-w-0 overflow-auto">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/queue" element={<LiveQueue mode="chats" />} />
          <Route path="/calls" element={<LiveQueue mode="calls" />} />
          <Route path="/cases" element={<Cases />} />
          <Route path="/suggestions" element={<Suggestions />} />
          <Route path="/sessions" element={<SessionViewer />} />
          <Route path="/reports" element={<Reports />} />
          <Route path="/gaps" element={<KnowledgeGapQueue />} />
          <Route path="/canned-replies" element={<CannedReplies />} />
          <Route path="/knowledge" element={<KnowledgeBase />} />
          <Route path="/rules" element={<Rules />} />
          <Route path="/users" element={<UserManagement />} />
          <Route path="/monitor" element={<SystemMonitor />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  )
}
