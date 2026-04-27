import React, { useState, useEffect } from 'react'
import { Routes, Route, Link, useLocation } from 'react-router-dom'
import Dashboard from './pages/Dashboard.jsx'
import LiveQueue from './pages/LiveQueue.jsx'
import SessionViewer from './pages/SessionViewer.jsx'
import KnowledgeBase from './pages/KnowledgeBase.jsx'
import Reports from './pages/Reports.jsx'

const API_BASE = import.meta.env.VITE_NURA_API_BASE || '/v1'
const API_KEY = import.meta.env.VITE_NURA_API_KEY || ''

export const api = { base: API_BASE, key: API_KEY }

const navItems = [
  { path: '/', label: 'Dashboard', icon: '📊' },
  { path: '/queue', label: 'Live Queue', icon: '🔔' },
  { path: '/sessions', label: 'Sessions', icon: '💬' },
  { path: '/reports', label: 'Reports', icon: '📈' },
  { path: '/knowledge', label: 'Knowledge Base', icon: '📚' },
]

function Sidebar({ pendingCount }) {
  const { pathname } = useLocation()
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
      <div className="p-4 text-xs text-gray-500 border-t border-gray-700">
        NURA v1.0 • Customer Support
      </div>
    </aside>
  )
}

export default function App() {
  const [pendingCount, setPendingCount] = useState(0)

  useEffect(() => {
    async function fetchPending() {
      try {
        const res = await fetch(`${API_BASE}/queue`, {
          headers: { Authorization: `Bearer ${API_KEY}` },
        })
        const data = await res.json()
        setPendingCount(data.pending || 0)
      } catch {}
    }
    fetchPending()
    const t = setInterval(fetchPending, 5000)
    return () => clearInterval(t)
  }, [])

  return (
    <div className="flex min-h-screen">
      <Sidebar pendingCount={pendingCount} />
      <main className="flex-1 overflow-auto">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/queue" element={<LiveQueue />} />
          <Route path="/sessions" element={<SessionViewer />} />
          <Route path="/reports" element={<Reports />} />
          <Route path="/knowledge" element={<KnowledgeBase />} />
        </Routes>
      </main>
    </div>
  )
}
