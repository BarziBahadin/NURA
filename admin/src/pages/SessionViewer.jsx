import React, { useState, useEffect, useCallback } from 'react'
import { api } from '../App.jsx'

const TABS = [
  { label: 'All', value: null },
  { label: 'Active', value: 'ACTIVE' },
  { label: 'Pending', value: 'PENDING_HANDOFF' },
  { label: 'With Agent', value: 'HUMAN_ACTIVE' },
  { label: 'Resolved', value: 'RESOLVED' },
]

const STATUS_STYLE = {
  ACTIVE:          { label: 'Active',      color: 'bg-green-100 text-green-700' },
  PENDING_HANDOFF: { label: 'Pending',     color: 'bg-yellow-100 text-yellow-700' },
  HUMAN_ACTIVE:    { label: 'With Agent',  color: 'bg-blue-100 text-blue-700' },
  RESOLVED:        { label: 'Resolved',    color: 'bg-gray-100 text-gray-500' },
}

function timeAgo(iso) {
  const diff = Math.floor((Date.now() - new Date(iso)) / 1000)
  if (diff < 60) return 'just now'
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  return `${Math.floor(diff / 86400)}d ago`
}

function HistoryPanel({ history }) {
  if (!history || history.length === 0)
    return <div className="text-center text-gray-400 text-xs py-4">No messages</div>
  return (
    <div className="space-y-2 max-h-72 overflow-y-auto p-3 bg-gray-50 rounded-xl">
      {history.map((turn, i) => (
        <div key={i} className={`flex gap-2 ${turn.role === 'customer' ? 'flex-row-reverse' : ''}`}>
          <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 ${
            turn.role === 'agent' ? 'bg-blue-100 text-blue-600' : 'bg-gray-200 text-gray-600'
          }`}>
            {turn.role === 'agent' ? 'A' : 'C'}
          </div>
          <div className={`flex flex-col ${turn.role === 'customer' ? 'items-end' : ''}`}>
            <div className={`px-3 py-1.5 rounded-2xl text-sm max-w-xs ${
              turn.role === 'agent'
                ? 'bg-white border border-gray-200 text-gray-800 rounded-tl-sm'
                : 'bg-blue-600 text-white rounded-tr-sm'
            }`}>
              {turn.message}
              {turn.attachment_url && turn.message_type === 'image' && (
                <img src={turn.attachment_url} alt="attachment"
                  className="mt-1 max-w-xs rounded-lg border cursor-pointer"
                  onClick={() => window.open(turn.attachment_url)} />
              )}
              {turn.attachment_url && turn.message_type === 'file' && (
                <a href={turn.attachment_url} target="_blank" rel="noreferrer"
                  className="block mt-1 text-blue-400 underline text-xs">📄 View attachment</a>
              )}
            </div>
            <div className="text-xs text-gray-400 mt-0.5 flex gap-1">
              {new Date(turn.timestamp).toLocaleTimeString('en', { hour: '2-digit', minute: '2-digit' })}
              {turn.confidence != null && <span>• {Math.round(turn.confidence * 100)}%</span>}
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

export default function SessionViewer() {
  const [activeTab, setActiveTab] = useState(null)
  const [sessions, setSessions] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState(null)
  const [resolving, setResolving] = useState({})
  const [search, setSearch] = useState('')

  const fetchSessions = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({ limit: 100 })
      if (activeTab) params.set('status', activeTab)
      const res = await fetch(`${api.base}/sessions/list?${params}`, {
        headers: { Authorization: `Bearer ${api.key}` },
      })
      const data = await res.json()
      setSessions(data.sessions || [])
      setTotal(data.total || 0)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }, [activeTab])

  useEffect(() => {
    setExpanded(null)
    fetchSessions()
  }, [fetchSessions])

  async function resolveSession(sessionId) {
    setResolving(r => ({ ...r, [sessionId]: true }))
    try {
      await fetch(`${api.base}/session/${sessionId}/resolve`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${api.key}` },
      })
      await fetchSessions()
      if (expanded === sessionId) setExpanded(null)
    } catch (e) {
      console.error(e)
    } finally {
      setResolving(r => ({ ...r, [sessionId]: false }))
    }
  }

  const filtered = sessions.filter(s => {
    if (!search.trim()) return true
    const q = search.trim().toLowerCase()
    return s.session_id.toLowerCase().includes(q) || s.customer_id.toLowerCase().includes(q)
  })

  return (
    <div className="p-6 max-w-5xl">
      <div className="flex items-center justify-between mb-5 flex-wrap gap-3">
        <h1 className="text-2xl font-bold text-gray-800">Sessions</h1>
        <button
          onClick={fetchSessions}
          className="text-sm bg-white border border-gray-200 hover:bg-gray-50 text-gray-500 px-3 py-1.5 rounded-lg transition"
        >
          ↻ Refresh
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-4 bg-gray-100 p-1 rounded-xl w-fit">
        {TABS.map(tab => (
          <button
            key={String(tab.value)}
            onClick={() => setActiveTab(tab.value)}
            className={`px-4 py-1.5 rounded-lg text-sm font-medium transition whitespace-nowrap ${
              activeTab === tab.value
                ? 'bg-white text-gray-800 shadow-sm'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Search */}
      <div className="mb-4">
        <input
          type="text"
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Search by session ID or customer..."
          className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
        />
      </div>

      {/* Count */}
      <div className="text-xs text-gray-400 mb-3">
        {loading ? 'Loading...' : `${filtered.length} session${filtered.length !== 1 ? 's' : ''}${total > filtered.length ? ` (of ${total})` : ''}`}
      </div>

      {/* Session list */}
      {loading ? (
        <div className="text-center text-gray-400 py-20 text-sm">Loading...</div>
      ) : filtered.length === 0 ? (
        <div className="bg-white rounded-2xl shadow p-12 text-center text-gray-400">
          <div className="text-4xl mb-3">📭</div>
          <div>No sessions found</div>
        </div>
      ) : (
        <div className="space-y-2">
          {filtered.map(s => {
            const st = STATUS_STYLE[s.status] || { label: s.status, color: 'bg-gray-100 text-gray-500' }
            const lastMsg = s.history?.[s.history.length - 1]
            const isExpanded = expanded === s.session_id
            const canResolve = s.status !== 'RESOLVED'

            return (
              <div key={s.session_id} className="bg-white rounded-2xl shadow overflow-hidden">
                {/* Row */}
                <div
                  className="flex items-center gap-3 p-4 cursor-pointer hover:bg-gray-50 transition"
                  onClick={() => setExpanded(isExpanded ? null : s.session_id)}
                >
                  <span className="text-gray-300 text-xs">{isExpanded ? '▲' : '▼'}</span>

                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium flex-shrink-0 ${st.color}`}>
                    {st.label}
                  </span>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-0.5">
                      <span className="font-mono text-xs text-gray-400">{s.session_id.slice(0, 8)}…</span>
                      <span className="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded-full">{s.channel}</span>
                    </div>
                    {lastMsg && (
                      <div className="text-sm text-gray-600 truncate">
                        {lastMsg.role === 'customer' ? '👤 ' : '🤖 '}{lastMsg.message}
                      </div>
                    )}
                  </div>

                  <div className="text-xs text-gray-400 hidden sm:block flex-shrink-0">
                    {s.customer_id}
                  </div>

                  <div className="text-xs text-gray-400 flex-shrink-0">
                    {s.history?.length || 0} msg
                  </div>

                  <div className="text-xs text-gray-400 flex-shrink-0">
                    {timeAgo(s.updated_at)}
                  </div>

                  {canResolve && (
                    <button
                      onClick={e => { e.stopPropagation(); resolveSession(s.session_id) }}
                      disabled={resolving[s.session_id]}
                      className="text-xs bg-red-50 hover:bg-red-100 text-red-600 px-3 py-1.5 rounded-lg transition disabled:opacity-50 flex-shrink-0"
                    >
                      {resolving[s.session_id] ? '...' : 'Resolve'}
                    </button>
                  )}
                </div>

                {/* Expanded history */}
                {isExpanded && (
                  <div className="border-t border-gray-100 p-4">
                    <div className="text-xs text-gray-400 mb-3 flex gap-4">
                      <span>Session: <span className="font-mono text-gray-600">{s.session_id}</span></span>
                      <span>Customer: <span className="text-gray-600">{s.customer_id}</span></span>
                      <span>Started: {new Date(s.created_at).toLocaleString('en')}</span>
                    </div>
                    <HistoryPanel history={s.history} />
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
