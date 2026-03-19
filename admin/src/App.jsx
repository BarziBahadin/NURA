import React from 'react'
import { Routes, Route, Link, useLocation } from 'react-router-dom'
import Dashboard from './pages/Dashboard.jsx'
import LiveQueue from './pages/LiveQueue.jsx'
import SessionViewer from './pages/SessionViewer.jsx'
import KnowledgeBase from './pages/KnowledgeBase.jsx'

const API_BASE = 'http://localhost:8000/v1'
const API_KEY = 'nura-dev-key-change-in-production'

export const api = { base: API_BASE, key: API_KEY }

const navItems = [
  { path: '/', label: 'لوحة التحكم', icon: '📊' },
  { path: '/queue', label: 'قائمة الانتظار', icon: '🔔' },
  { path: '/sessions', label: 'المحادثات', icon: '💬' },
  { path: '/knowledge', label: 'قاعدة المعرفة', icon: '📚' },
]

function Sidebar() {
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
            <span>{label}</span>
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
  return (
    <div className="flex min-h-screen" style={{ direction: 'rtl' }}>
      <Sidebar />
      <main className="flex-1 overflow-auto">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/queue" element={<LiveQueue />} />
          <Route path="/sessions" element={<SessionViewer />} />
          <Route path="/knowledge" element={<KnowledgeBase />} />
        </Routes>
      </main>
    </div>
  )
}
