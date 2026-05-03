import React, { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../App.jsx'

const EVENT_COLORS = {
  message:      'bg-green-100 text-green-700',
  login:        'bg-blue-100 text-blue-700',
  escalation:   'bg-orange-100 text-orange-700',
  resolved:     'bg-gray-100 text-gray-500',
  llm_call:     'bg-purple-100 text-purple-700',
  admin_action: 'bg-red-100 text-red-600',
}

const STATUS_COLORS = {
  ACTIVE:          'bg-green-100 text-green-700',
  PENDING_HANDOFF: 'bg-yellow-100 text-yellow-700',
  HUMAN_ACTIVE:    'bg-blue-100 text-blue-700',
}

function StatCard({ label, value, sub }) {
  return (
    <div className="bg-white rounded-xl shadow px-4 py-3 flex flex-col min-w-[110px]">
      <div className="text-xs text-gray-400">{label}</div>
      <div className="text-2xl font-bold text-gray-800">{value ?? '—'}</div>
      {sub && <div className="text-xs text-gray-400">{sub}</div>}
    </div>
  )
}

function StatsBar({ stats }) {
  return (
    <div className="flex flex-wrap gap-3 mb-6">
      <StatCard label="Active Sessions" value={stats?.active_sessions} />
      <StatCard label="Queue" value={stats?.pending_handoff} />
      <StatCard label="With Agent" value={stats?.human_active} />
      <StatCard label="Msgs / hr" value={stats?.messages_last_hour} />
      <StatCard label="Cost Today" value={stats ? `$${stats.cost_today_usd}` : null} />
      <StatCard label="Escalation Rate" value={stats ? `${stats.escalation_rate_today_pct}%` : null} sub="today" />
    </div>
  )
}

function LiveFeedTab() {
  const [events, setEvents] = useState([])
  const [paused, setPaused] = useState(false)
  const [filter, setFilter] = useState('all')
  const pausedRef = useRef(false)

  useEffect(() => { pausedRef.current = paused }, [paused])

  useEffect(() => {
    async function fetchEvents() {
      if (pausedRef.current) return
      try {
        const res = await fetch(`${api.base}/monitor/activity?limit=100`, {
          headers: { Authorization: `Bearer ${api.key}` },
        })
        const data = await res.json()
        setEvents(data.events || [])
      } catch {}
    }
    fetchEvents()
    const t = setInterval(fetchEvents, 3000)
    return () => clearInterval(t)
  }, [])

  const FILTERS = ['all', 'message', 'escalation', 'admin_action', 'llm_call', 'resolved']
  const visible = filter === 'all' ? events : events.filter(e => e.type === filter)

  return (
    <div>
      <div className="flex flex-wrap items-center gap-2 mb-3">
        {FILTERS.map(f => (
          <button key={f} onClick={() => setFilter(f)}
            className={`text-xs px-3 py-1 rounded-full transition ${filter === f ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}>
            {f === 'all' ? 'All' : f.replace('_', ' ')}
          </button>
        ))}
        <button onClick={() => setPaused(p => !p)}
          className={`ml-auto text-xs px-3 py-1 rounded-full transition ${paused ? 'bg-orange-100 text-orange-700' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}>
          {paused ? '▶ Resume' : '⏸ Pause'}
        </button>
      </div>
      <div className="bg-white rounded-2xl shadow overflow-hidden">
        <table className="w-full text-xs">
          <thead className="bg-gray-50 border-b border-gray-100">
            <tr>
              <th className="text-left px-4 py-2.5 text-gray-500 font-semibold uppercase tracking-wide w-36">Time</th>
              <th className="text-left px-4 py-2.5 text-gray-500 font-semibold uppercase tracking-wide w-28">Type</th>
              <th className="text-left px-4 py-2.5 text-gray-500 font-semibold uppercase tracking-wide">Actor</th>
              <th className="text-left px-4 py-2.5 text-gray-500 font-semibold uppercase tracking-wide">Description</th>
              <th className="text-left px-4 py-2.5 text-gray-500 font-semibold uppercase tracking-wide w-20">Channel</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {visible.map((e, i) => (
              <tr key={i} className="hover:bg-gray-50">
                <td className="px-4 py-2 text-gray-400 whitespace-nowrap">
                  {new Date(e.created_at).toLocaleTimeString('en', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                </td>
                <td className="px-4 py-2">
                  <span className={`px-2 py-0.5 rounded-full font-medium ${EVENT_COLORS[e.type] || 'bg-gray-100 text-gray-600'}`}>
                    {e.type.replace('_', ' ')}
                  </span>
                </td>
                <td className="px-4 py-2 text-gray-600 max-w-[120px] truncate">{e.actor || '—'}</td>
                <td className="px-4 py-2 text-gray-700 max-w-xs truncate">{e.description}</td>
                <td className="px-4 py-2 text-gray-400">{e.channel || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {visible.length === 0 && (
          <div className="text-center text-gray-400 py-12">No events</div>
        )}
      </div>
    </div>
  )
}

function LiveSessionsTab() {
  const [sessions, setSessions] = useState([])
  const navigate = useNavigate()

  useEffect(() => {
    async function fetchLive() {
      try {
        const res = await fetch(`${api.base}/monitor/sessions/live`, {
          headers: { Authorization: `Bearer ${api.key}` },
        })
        const data = await res.json()
        setSessions(data.sessions || [])
      } catch {}
    }
    fetchLive()
    const t = setInterval(fetchLive, 5000)
    return () => clearInterval(t)
  }, [])

  return (
    <div className="bg-white rounded-2xl shadow overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-gray-50 border-b border-gray-100">
          <tr>
            <th className="text-left px-5 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Session</th>
            <th className="text-left px-5 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Customer</th>
            <th className="text-left px-5 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Channel</th>
            <th className="text-left px-5 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Status</th>
            <th className="text-left px-5 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Messages</th>
            <th className="text-left px-5 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Last Activity</th>
            <th className="text-left px-5 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Assigned To</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-50">
          {sessions.map(s => (
            <tr key={s.session_id}
              className="hover:bg-gray-50 cursor-pointer transition"
              onClick={() => navigate('/sessions')}>
              <td className="px-5 py-3 font-mono text-xs text-gray-400">{s.session_id.slice(0, 8)}…</td>
              <td className="px-5 py-3 text-gray-700">{s.customer_id}</td>
              <td className="px-5 py-3 text-gray-500">{s.channel}</td>
              <td className="px-5 py-3">
                <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${STATUS_COLORS[s.status] || 'bg-gray-100 text-gray-500'}`}>
                  {s.status}
                </span>
              </td>
              <td className="px-5 py-3 text-gray-500">{s.message_count}</td>
              <td className="px-5 py-3 text-xs text-gray-400">
                {new Date(s.last_activity).toLocaleTimeString('en', { hour: '2-digit', minute: '2-digit' })}
              </td>
              <td className="px-5 py-3 text-gray-500">{s.assigned_to || '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {sessions.length === 0 && (
        <div className="text-center text-gray-400 py-12">No active sessions</div>
      )}
    </div>
  )
}

function AuditLogTab() {
  const [entries, setEntries] = useState([])
  const [total, setTotal] = useState(0)
  const [offset, setOffset] = useState(0)
  const [actor, setActor] = useState('')
  const [action, setAction] = useState('')
  const LIMIT = 50

  async function fetchLog(off = 0) {
    const params = new URLSearchParams({ limit: LIMIT, offset: off })
    if (actor) params.set('actor', actor)
    if (action) params.set('action', action)
    try {
      const res = await fetch(`${api.base}/monitor/audit-log?${params}`, {
        headers: { Authorization: `Bearer ${api.key}` },
      })
      const data = await res.json()
      setEntries(data.entries || [])
      setTotal(data.total || 0)
      setOffset(off)
    } catch {}
  }

  useEffect(() => { fetchLog(0) }, [])

  return (
    <div>
      <div className="flex gap-2 mb-3">
        <input value={actor} onChange={e => setActor(e.target.value)} placeholder="Filter by actor"
          className="border border-gray-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
        <input value={action} onChange={e => setAction(e.target.value)} placeholder="Filter by action"
          className="border border-gray-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
        <button onClick={() => fetchLog(0)}
          className="bg-blue-600 hover:bg-blue-700 text-white text-sm px-4 py-2 rounded-xl transition">
          Search
        </button>
      </div>
      <div className="bg-white rounded-2xl shadow overflow-hidden">
        <table className="w-full text-xs">
          <thead className="bg-gray-50 border-b border-gray-100">
            <tr>
              <th className="text-left px-4 py-2.5 text-gray-500 font-semibold uppercase tracking-wide w-36">Time</th>
              <th className="text-left px-4 py-2.5 text-gray-500 font-semibold uppercase tracking-wide">Actor</th>
              <th className="text-left px-4 py-2.5 text-gray-500 font-semibold uppercase tracking-wide">Action</th>
              <th className="text-left px-4 py-2.5 text-gray-500 font-semibold uppercase tracking-wide">Target</th>
              <th className="text-left px-4 py-2.5 text-gray-500 font-semibold uppercase tracking-wide">Detail</th>
              <th className="text-left px-4 py-2.5 text-gray-500 font-semibold uppercase tracking-wide w-28">IP</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {entries.map((e, i) => (
              <tr key={i} className="hover:bg-gray-50">
                <td className="px-4 py-2 text-gray-400 whitespace-nowrap">
                  {new Date(e.created_at).toLocaleString('en', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                </td>
                <td className="px-4 py-2 font-medium text-gray-700">{e.actor || '—'}</td>
                <td className="px-4 py-2 text-gray-600">{e.action}</td>
                <td className="px-4 py-2 text-gray-500">{e.target || '—'}</td>
                <td className="px-4 py-2 text-gray-400 max-w-[180px] truncate">{e.detail || '—'}</td>
                <td className="px-4 py-2 text-gray-400 font-mono">{e.ip || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {entries.length === 0 && (
          <div className="text-center text-gray-400 py-12">No audit entries</div>
        )}
      </div>
      {total > LIMIT && (
        <div className="flex items-center justify-between mt-3 text-sm text-gray-500">
          <span>{offset + 1}–{Math.min(offset + LIMIT, total)} of {total}</span>
          <div className="flex gap-2">
            <button disabled={offset === 0} onClick={() => fetchLog(offset - LIMIT)}
              className="px-3 py-1.5 rounded-lg bg-gray-100 hover:bg-gray-200 disabled:opacity-40">← Prev</button>
            <button disabled={offset + LIMIT >= total} onClick={() => fetchLog(offset + LIMIT)}
              className="px-3 py-1.5 rounded-lg bg-gray-100 hover:bg-gray-200 disabled:opacity-40">Next →</button>
          </div>
        </div>
      )}
    </div>
  )
}

const TABS = [
  { key: 'feed', label: 'Live Feed' },
  { key: 'sessions', label: 'Live Sessions' },
  { key: 'audit', label: 'Audit Log' },
]

export default function SystemMonitor() {
  const [tab, setTab] = useState('feed')
  const [stats, setStats] = useState(null)

  useEffect(() => {
    async function fetchStats() {
      try {
        const res = await fetch(`${api.base}/monitor/stats/realtime`, {
          headers: { Authorization: `Bearer ${api.key}` },
        })
        const data = await res.json()
        setStats(data)
      } catch {}
    }
    fetchStats()
    const t = setInterval(fetchStats, 5000)
    return () => clearInterval(t)
  }, [])

  return (
    <div className="p-6 max-w-7xl">
      <h1 className="text-2xl font-bold text-gray-800 mb-4">System Monitor</h1>
      <StatsBar stats={stats} />

      <div className="flex gap-1 mb-5 bg-gray-100 p-1 rounded-xl w-fit">
        {TABS.map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`px-5 py-1.5 rounded-lg text-sm font-medium transition ${
              tab === t.key ? 'bg-white text-gray-800 shadow-sm' : 'text-gray-500 hover:text-gray-700'
            }`}>
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'feed' && <LiveFeedTab />}
      {tab === 'sessions' && <LiveSessionsTab />}
      {tab === 'audit' && <AuditLogTab />}
    </div>
  )
}
