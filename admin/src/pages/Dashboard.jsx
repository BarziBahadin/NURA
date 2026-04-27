import React, { useState, useEffect, useCallback } from 'react'
import {
  LineChart, Line, BarChart, Bar,
  PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts'
import { api } from '../App.jsx'

// ── helpers ──────────────────────────────────────────────────────────────────

const SOURCE_COLORS = {
  openai:      '#7c3aed',
  rag:         '#10b981',
  'rule-based':'#f59e0b',
  escalated:   '#ef4444',
}
const SOURCE_LABELS = {
  openai: 'AI (OpenAI)', rag: 'RAG', 'rule-based': 'Rules', escalated: 'Escalated',
}
const EVENT_LABELS = {
  chat_open: 'Chat Opened', chat_close: 'Chat Closed',
  send_message: 'Message Sent', lang_switch: 'Language Switch',
  tree_click: 'Tree Topic', tree_back: 'Tree Back',
  tree_home: 'Tree Home', followup_yes: 'Follow-up: Yes',
  followup_no: 'Follow-up: No', feedback_good: 'Feedback ✓', feedback_bad: 'Feedback ✗',
}

function srcColor(key) { return SOURCE_COLORS[key] || '#6b7280' }
function srcLabel(key) { return SOURCE_LABELS[key] || key }

function exportCSV(rows) {
  const headers = ['session_id','channel','customer_message','source','confidence','escalated','created_at']
  const lines = [headers.join(','), ...rows.map(r => headers.map(h => JSON.stringify(r[h] ?? '')).join(','))]
  const a = Object.assign(document.createElement('a'), {
    href: URL.createObjectURL(new Blob([lines.join('\n')], { type: 'text/csv' })),
    download: `nura_${new Date().toISOString().slice(0,10)}.csv`,
  })
  a.click()
}

// ── small components ─────────────────────────────────────────────────────────

function KpiCard({ label, value, sub, color = 'text-gray-800', alert = false }) {
  return (
    <div className={`bg-white rounded-2xl shadow p-5 ${alert ? 'ring-2 ring-red-400' : ''}`}>
      <div className="text-xs text-gray-400 mb-1 uppercase tracking-wide">{label}</div>
      <div className={`text-3xl font-bold ${color}`}>{value}</div>
      {sub && <div className="text-xs text-gray-400 mt-1">{sub}</div>}
    </div>
  )
}

function SectionCard({ title, children, action }) {
  return (
    <div className="bg-white rounded-2xl shadow p-5">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold text-gray-600 uppercase tracking-wide">{title}</h2>
        {action}
      </div>
      {children}
    </div>
  )
}

function HorizBar({ label, count, max, color }) {
  const pct = max > 0 ? Math.round((count / max) * 100) : 0
  return (
    <div className="flex items-center gap-3 mb-2">
      <div className="w-36 text-xs text-gray-500 truncate">{label}</div>
      <div className="flex-1 bg-gray-100 rounded-full h-2.5">
        <div className="h-2.5 rounded-full transition-all" style={{ width: `${pct}%`, background: color }} />
      </div>
      <div className="w-10 text-xs text-gray-500 text-right">{count}</div>
    </div>
  )
}

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-white border border-gray-200 rounded-xl px-3 py-2 shadow text-xs">
      <div className="text-gray-500 mb-1">{label}</div>
      {payload.map((p, i) => (
        <div key={i} style={{ color: p.color }}>{p.name}: <strong>{p.value}</strong></div>
      ))}
    </div>
  )
}

// ── main component ────────────────────────────────────────────────────────────

export default function Dashboard() {
  const [data, setData]           = useState(null)
  const [health, setHealth]       = useState(null)
  const [days, setDays]           = useState(30)
  const [loading, setLoading]     = useState(true)
  const [lastUpdated, setLastUpdated] = useState(null)
  const [secondsAgo, setSecondsAgo]   = useState(0)

  const fetchData = useCallback(async () => {
    try {
      const h = { Authorization: `Bearer ${api.key}` }
      const [analytics, healthData] = await Promise.all([
        fetch(`${api.base}/analytics/dashboard?days=${days}`, { headers: h }).then(r => r.json()),
        fetch(`${api.base}/health`, { headers: h }).then(r => r.json()),
      ])
      setData(analytics)
      setHealth(healthData)
      setLastUpdated(Date.now())
      setSecondsAgo(0)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }, [days])

  useEffect(() => { setLoading(true); fetchData() }, [fetchData])
  useEffect(() => {
    const t = setInterval(fetchData, 60000)
    return () => clearInterval(t)
  }, [fetchData])
  useEffect(() => {
    if (!lastUpdated) return
    const t = setInterval(() => setSecondsAgo(Math.round((Date.now() - lastUpdated) / 1000)), 5000)
    return () => clearInterval(t)
  }, [lastUpdated])

  const escalationAlert = data && data.escalation_rate > 0.2

  const hourlyData = data
    ? Array.from({ length: 24 }, (_, displayHour) => {
        const utcHour = (displayHour - 3 + 24) % 24
        return {
          hour: `${displayHour}:00`,
          messages: data.hourly_distribution.find(r => r.hour === utcHour)?.messages || 0,
        }
      })
    : []

  const pieData = data
    ? Object.entries(data.source_breakdown).map(([key, value]) => ({
        name: srcLabel(key), value, color: srcColor(key),
      }))
    : []

  const totalClicks = data?.top_tree_topics?.reduce((s, t) => s + t.clicks, 0) || 0
  const maxTopicClicks = data?.top_tree_topics?.[0]?.clicks || 1
  const maxEventCount  = data?.event_breakdown?.[0]?.count || 1

  return (
    <div className="p-6 max-w-6xl">

      {/* Header */}
      <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Dashboard</h1>
          {lastUpdated && (
            <div className="text-xs text-gray-400 mt-0.5">
              Last updated: {secondsAgo < 10 ? 'just now' : `${secondsAgo}s ago`} • auto-refreshes every minute
            </div>
          )}
        </div>
        <div className="flex items-center gap-2">
          {[7, 30, 90].map(d => (
            <button key={d} onClick={() => setDays(d)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition ${
                days === d ? 'bg-blue-600 text-white' : 'bg-white text-gray-600 border border-gray-200 hover:bg-gray-50'
              }`}>
              {d}d
            </button>
          ))}
          <button onClick={fetchData}
            className="px-3 py-1.5 rounded-lg text-sm bg-white border border-gray-200 hover:bg-gray-50 text-gray-500">
            ↻ Refresh
          </button>
        </div>
      </div>

      {/* Alert */}
      {escalationAlert && (
        <div className="mb-5 bg-red-50 border border-red-200 text-red-700 rounded-xl px-4 py-3 text-sm flex items-center gap-2">
          ⚠️ Escalation rate is high ({Math.round(data.escalation_rate * 100)}%) — exceeds 20%
        </div>
      )}

      {loading ? (
        <div className="text-center text-gray-400 py-20 text-sm">Loading data...</div>
      ) : !data ? (
        <div className="text-center text-red-400 py-20 text-sm">Failed to load data — make sure the API is running</div>
      ) : (
        <>
          {/* KPI row */}
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-4 mb-6">
            <KpiCard label="Total Sessions"  value={data.total_sessions.toLocaleString()} sub={`last ${days} days`} />
            <KpiCard label="Total Messages"  value={data.total_messages.toLocaleString()}
              sub={`${data.total_sessions > 0 ? (data.total_messages / data.total_sessions).toFixed(1) : 0} msg/session`} />
            <KpiCard label="Avg Confidence"
              value={`${Math.round(data.avg_confidence * 100)}%`}
              sub="automated response accuracy"
              color={data.avg_confidence >= 0.8 ? 'text-green-600' : data.avg_confidence >= 0.6 ? 'text-yellow-600' : 'text-red-600'} />
            <KpiCard label="Escalation Rate"
              value={`${Math.round(data.escalation_rate * 100)}%`}
              sub={`${data.escalations} escalations`}
              color={escalationAlert ? 'text-red-600' : 'text-gray-800'}
              alert={escalationAlert} />
            <KpiCard label="Tree Clicks" value={totalClicks.toLocaleString()} sub="total guided interactions" />
          </div>

          {/* Daily traffic + Source donut */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
            <div className="sm:col-span-2">
              <SectionCard title="Daily Traffic">
                <ResponsiveContainer width="100%" height={220}>
                  <LineChart data={data.daily_volume} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis dataKey="date" tick={{ fontSize: 10 }} tickFormatter={v => v.slice(5)} />
                    <YAxis tick={{ fontSize: 10 }} />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend iconSize={10} wrapperStyle={{ fontSize: 11 }} />
                    <Line type="monotone" dataKey="messages" name="Messages" stroke="#3b82f6" strokeWidth={2} dot={false} />
                    <Line type="monotone" dataKey="sessions" name="Sessions" stroke="#7c3aed" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </SectionCard>
            </div>

            <SectionCard title="Response Sources">
              {pieData.length === 0 ? (
                <div className="text-xs text-gray-400 py-8 text-center">No data</div>
              ) : (
                <ResponsiveContainer width="100%" height={220}>
                  <PieChart>
                    <Pie data={pieData} cx="50%" cy="45%" innerRadius={55} outerRadius={85}
                      paddingAngle={3} dataKey="value">
                      {pieData.map((entry, i) => <Cell key={i} fill={entry.color} />)}
                    </Pie>
                    <Tooltip formatter={(v, n) => [`${v} messages`, n]} />
                    <Legend iconSize={10} wrapperStyle={{ fontSize: 11 }} />
                  </PieChart>
                </ResponsiveContainer>
              )}
            </SectionCard>
          </div>

          {/* Hourly + Health */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
            <SectionCard title="Hourly Message Distribution">
              <ResponsiveContainer width="100%" height={180}>
                <BarChart data={hourlyData} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" vertical={false} />
                  <XAxis dataKey="hour" tick={{ fontSize: 9 }} interval={3} />
                  <YAxis tick={{ fontSize: 10 }} />
                  <Tooltip content={<CustomTooltip />} />
                  <Bar dataKey="messages" name="Messages" fill="#6366f1" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
              {data.hourly_distribution.length > 0 && (() => {
                const peak = data.hourly_distribution.reduce((a, b) => a.messages > b.messages ? a : b)
                const peakLocal = (peak.hour + 3) % 24
                return <div className="text-xs text-gray-400 mt-2 text-center">Busiest hour: {peakLocal}:00 — {peak.messages} messages</div>
              })()}
            </SectionCard>

            {health && (
              <SectionCard title="Service Health">
                <div className="grid grid-cols-2 gap-2">
                  {Object.entries(health.services).map(([name, status]) => (
                    <div key={name} className="flex items-center gap-2 bg-gray-50 rounded-xl px-3 py-2">
                      <span className={`w-2 h-2 rounded-full flex-shrink-0 ${status === 'ok' ? 'bg-green-400 animate-pulse' : 'bg-red-500'}`} />
                      <span className="text-xs text-gray-600 flex-1">{name}</span>
                      <span className={`text-xs ${status === 'ok' ? 'text-green-500' : 'text-red-500'}`}>{status}</span>
                    </div>
                  ))}
                </div>
              </SectionCard>
            )}
          </div>

          {/* Button events + Top topics */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
            <SectionCard title="Widget Interactions">
              {data.event_breakdown.length === 0 ? (
                <div className="text-xs text-gray-400">No events recorded yet</div>
              ) : data.event_breakdown.map(e => (
                <HorizBar key={e.event_type}
                  label={EVENT_LABELS[e.event_type] || e.event_type}
                  count={e.count} max={maxEventCount} color="#7c3aed" />
              ))}
            </SectionCard>

            <SectionCard title="Top Tree Topics">
              {data.top_tree_topics.length === 0 ? (
                <div className="text-xs text-gray-400">No tree clicks recorded yet</div>
              ) : data.top_tree_topics.slice(0, 10).map(t => (
                <HorizBar key={t.topic_id} label={t.topic_label}
                  count={t.clicks} max={maxTopicClicks} color="#ea580c" />
              ))}
            </SectionCard>
          </div>

          {/* Recent conversations */}
          <SectionCard title="Recent Conversations"
            action={
              <button onClick={() => exportCSV(data.recent_conversations)}
                className="text-xs bg-gray-100 hover:bg-gray-200 text-gray-600 px-3 py-1.5 rounded-lg transition">
                Export CSV ↓
              </button>
            }>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-100 text-xs text-gray-400">
                    {['Session','Message','Source','Confidence','Status','Time'].map(h => (
                      <th key={h} className="pb-2 text-left font-medium">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data.recent_conversations.slice(0, 20).map((r, i) => (
                    <tr key={i} className="border-b border-gray-50 hover:bg-gray-50 transition">
                      <td className="py-2 font-mono text-xs text-gray-400">{r.session_id.slice(0,8)}…</td>
                      <td className="py-2 text-gray-700 max-w-xs truncate">{r.customer_message}</td>
                      <td className="py-2">
                        {r.source
                          ? <span className="px-2 py-0.5 rounded-full text-xs font-medium"
                              style={{ background: srcColor(r.source) + '20', color: srcColor(r.source) }}>
                              {srcLabel(r.source)}
                            </span>
                          : <span className="text-gray-300">—</span>}
                      </td>
                      <td className="py-2 text-xs font-medium"
                        style={{ color: r.confidence >= 0.8 ? '#16a34a' : r.confidence >= 0.5 ? '#ca8a04' : '#dc2626' }}>
                        {Math.round(r.confidence * 100)}%
                      </td>
                      <td className="py-2">
                        {r.escalated
                          ? <span className="bg-red-100 text-red-600 text-xs px-2 py-0.5 rounded-full">Escalated</span>
                          : <span className="bg-green-100 text-green-600 text-xs px-2 py-0.5 rounded-full">Automated</span>}
                      </td>
                      <td className="py-2 text-xs text-gray-400 whitespace-nowrap">
                        {new Date(r.created_at).toLocaleDateString('en', { month:'short', day:'numeric', hour:'2-digit', minute:'2-digit' })}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </SectionCard>
        </>
      )}
    </div>
  )
}
