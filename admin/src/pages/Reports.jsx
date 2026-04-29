import React, { useEffect, useState, useCallback } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell, PieChart, Pie, Legend,
} from 'recharts'
import { api } from '../App.jsx'

const TABS = [
  ['gaps',     'Knowledge Gaps'],
  ['intents',  'Intents'],
  ['handoffs', 'Handoffs'],
  ['outcomes', 'Outcomes'],
  ['costs',    'Cost'],
  ['feedback', 'Bad Feedback'],
]

const INTENT_COLORS = ['#3b82f6','#7c3aed','#10b981','#f59e0b','#ef4444','#06b6d4','#ec4899','#14b8a6']
const HANDOFF_COLORS = ['#ef4444','#f97316','#eab308','#a855f7','#6366f1','#64748b']

// ── helpers ────────────────────────────────────────────────────────────────────

function fmtCost(n) {
  if (n >= 1) return `$${n.toFixed(2)}`
  if (n >= 0.01) return `$${n.toFixed(4)}`
  return `$${n.toFixed(6)}`
}

function fmtSec(s) {
  if (!s) return '—'
  if (s < 60) return `${Math.round(s)}s`
  if (s < 3600) return `${Math.floor(s / 60)}m ${Math.round(s % 60)}s`
  return `${Math.floor(s / 3600)}h ${Math.floor((s % 3600) / 60)}m`
}

function exportCSV(filename, columns, rows) {
  const header = columns.map(c => c.label).join(',')
  const lines = rows.map(r =>
    columns.map(c => JSON.stringify(r[c.key] ?? '')).join(',')
  )
  const blob = new Blob([[header, ...lines].join('\n')], { type: 'text/csv' })
  const a = Object.assign(document.createElement('a'), {
    href: URL.createObjectURL(blob),
    download: `${filename}_${new Date().toISOString().slice(0, 10)}.csv`,
  })
  a.click()
}

// ── small components ──────────────────────────────────────────────────────────

function Section({ title, children, onExport }) {
  return (
    <div className="bg-white rounded-2xl shadow p-5">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold text-gray-600 uppercase tracking-wide">{title}</h2>
        {onExport && (
          <button
            onClick={onExport}
            className="text-xs bg-gray-100 hover:bg-gray-200 text-gray-600 px-3 py-1.5 rounded-lg transition"
          >
            Export CSV ↓
          </button>
        )}
      </div>
      {children}
    </div>
  )
}

function Empty() {
  return <div className="text-sm text-gray-400 py-8 text-center">No data for this period</div>
}

function KpiRow({ items }) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-5">
      {items.map(({ label, value, sub, color = 'text-gray-800' }) => (
        <div key={label} className="bg-white rounded-2xl shadow p-4">
          <div className="text-xs text-gray-400 uppercase tracking-wide mb-1">{label}</div>
          <div className={`text-2xl font-bold ${color}`}>{value}</div>
          {sub && <div className="text-xs text-gray-400 mt-0.5">{sub}</div>}
        </div>
      ))}
    </div>
  )
}

function SimpleTable({ columns, rows }) {
  if (!rows?.length) return <Empty />
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-100 text-xs text-gray-400">
            {columns.map(c => (
              <th key={c.key} className="text-left font-medium pb-2 pr-4">{c.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} className="border-b border-gray-50 hover:bg-gray-50 transition">
              {columns.map(c => (
                <td key={c.key} className="py-2 pr-4 text-gray-700 max-w-xs truncate">
                  {c.render ? c.render(r) : (r[c.key] ?? '—')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

const ChartTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-white border border-gray-200 rounded-xl px-3 py-2 shadow text-xs">
      <div className="text-gray-500 mb-1">{label}</div>
      {payload.map((p, i) => (
        <div key={i} style={{ color: p.fill || p.color }}>
          {p.name}: <strong>{p.value}</strong>
        </div>
      ))}
    </div>
  )
}

// ── tab content ────────────────────────────────────────────────────────────────

function GapsTab({ data }) {
  const rows = data?.knowledge_gaps || []
  const cols = [
    { key: 'message_text', label: 'Customer Message' },
    { key: 'intent',       label: 'Intent' },
    { key: 'sub_intent',   label: 'Sub-Intent' },
    { key: 'gap_reason',   label: 'Gap Reason' },
    { key: 'channel',      label: 'Channel' },
    { key: 'created_at',   label: 'Time', render: r => new Date(r.created_at).toLocaleString() },
  ]
  return (
    <Section
      title={`Knowledge Gaps (${rows.length})`}
      onExport={() => exportCSV('knowledge_gaps', cols, rows)}
    >
      <SimpleTable columns={cols} rows={rows} />
    </Section>
  )
}

function IntentsTab({ data }) {
  const rows = data?.intents || []
  const chartData = rows.slice(0, 12).map(r => ({
    name: r.intent || 'unknown',
    count: r.count,
  }))
  const cols = [
    { key: 'intent',     label: 'Intent' },
    { key: 'sub_intent', label: 'Sub-Intent' },
    { key: 'count',      label: 'Count' },
  ]
  return (
    <div className="space-y-4">
      {chartData.length > 0 && (
        <div className="bg-white rounded-2xl shadow p-5">
          <h2 className="text-sm font-semibold text-gray-600 uppercase tracking-wide mb-4">Intent Distribution</h2>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={chartData} margin={{ top: 4, right: 8, left: -20, bottom: 60 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" vertical={false} />
              <XAxis dataKey="name" tick={{ fontSize: 10 }} angle={-35} textAnchor="end" interval={0} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip content={<ChartTooltip />} />
              <Bar dataKey="count" name="Messages" radius={[3, 3, 0, 0]}>
                {chartData.map((_, i) => (
                  <Cell key={i} fill={INTENT_COLORS[i % INTENT_COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
      <Section
        title="Intent Breakdown"
        onExport={() => exportCSV('intents', cols, rows)}
      >
        <SimpleTable columns={cols} rows={rows} />
      </Section>
    </div>
  )
}

function HandoffsTab({ data }) {
  const rows = data?.handoffs || []
  const total = rows.reduce((s, r) => s + r.count, 0)
  const pieData = rows.map((r, i) => ({
    name: r.reason,
    value: r.count,
    color: HANDOFF_COLORS[i % HANDOFF_COLORS.length],
  }))
  const cols = [
    { key: 'reason', label: 'Trigger Reason' },
    { key: 'count',  label: 'Count' },
    { key: '_pct',   label: '%', render: r => total ? `${Math.round(r.count / total * 100)}%` : '—' },
  ]
  return (
    <div className="space-y-4">
      {pieData.length > 0 && (
        <div className="bg-white rounded-2xl shadow p-5">
          <h2 className="text-sm font-semibold text-gray-600 uppercase tracking-wide mb-4">
            Handoff Reasons — {total} total
          </h2>
          <div className="flex flex-col sm:flex-row items-center gap-6">
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie data={pieData} cx="50%" cy="45%" innerRadius={55} outerRadius={85}
                  paddingAngle={3} dataKey="value">
                  {pieData.map((e, i) => <Cell key={i} fill={e.color} />)}
                </Pie>
                <Tooltip formatter={(v, n) => [`${v} sessions`, n]} />
                <Legend iconSize={10} wrapperStyle={{ fontSize: 11 }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
      <Section
        title="Handoff Reason Breakdown"
        onExport={() => exportCSV('handoffs', cols, rows)}
      >
        <SimpleTable columns={cols} rows={rows} />
      </Section>
    </div>
  )
}

function OutcomesTab({ data }) {
  const rows = data?.outcomes || []
  const cols = [
    { key: 'status',         label: 'Status' },
    { key: 'issue_category', label: 'Category' },
    { key: 'root_cause',     label: 'Root Cause' },
    { key: 'count',          label: 'Count' },
    { key: 'avg_resolution', label: 'Avg Resolution', render: r => fmtSec(r.avg_resolution) },
  ]
  const chartData = rows.slice(0, 10).map(r => ({
    name: r.issue_category || r.status || 'unknown',
    count: r.count,
    avg_resolution: Math.round(r.avg_resolution || 0),
  }))
  return (
    <div className="space-y-4">
      {chartData.length > 0 && (
        <div className="bg-white rounded-2xl shadow p-5">
          <h2 className="text-sm font-semibold text-gray-600 uppercase tracking-wide mb-4">Top Issue Categories</h2>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={chartData} margin={{ top: 4, right: 8, left: -20, bottom: 50 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" vertical={false} />
              <XAxis dataKey="name" tick={{ fontSize: 10 }} angle={-30} textAnchor="end" interval={0} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip content={<ChartTooltip />} />
              <Bar dataKey="count" name="Sessions" fill="#7c3aed" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
      <Section
        title="Resolution Outcomes"
        onExport={() => exportCSV('outcomes', cols, rows)}
      >
        <SimpleTable columns={cols} rows={rows} />
      </Section>
    </div>
  )
}

function CostTab({ data }) {
  const rows = data?.costs || []
  const totalCost = rows.reduce((s, r) => s + (r.estimated_cost || 0), 0)
  const totalTokens = rows.reduce((s, r) => s + (r.total_tokens || 0), 0)
  const cols = [
    { key: 'model',             label: 'Model' },
    { key: 'operation',         label: 'Operation' },
    { key: 'prompt_tokens',     label: 'Prompt Tokens' },
    { key: 'completion_tokens', label: 'Completion Tokens' },
    { key: 'total_tokens',      label: 'Total Tokens' },
    { key: 'estimated_cost',    label: 'Est. Cost', render: r => fmtCost(r.estimated_cost || 0) },
  ]
  const chartData = rows.map(r => ({
    name: `${r.model} / ${r.operation}`,
    cost: r.estimated_cost || 0,
    tokens: r.total_tokens || 0,
  }))
  return (
    <div className="space-y-4">
      <KpiRow items={[
        { label: 'Total Est. Cost', value: fmtCost(totalCost), color: totalCost > 1 ? 'text-red-600' : 'text-green-600' },
        { label: 'Total Tokens',    value: totalTokens.toLocaleString() },
        { label: 'API Calls (rows)', value: rows.length.toString() },
        { label: 'Avg Cost / Call', value: rows.length ? fmtCost(totalCost / rows.length) : '—' },
      ]} />
      {chartData.length > 0 && (
        <div className="bg-white rounded-2xl shadow p-5">
          <h2 className="text-sm font-semibold text-gray-600 uppercase tracking-wide mb-4">Cost by Model & Operation</h2>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={chartData} margin={{ top: 4, right: 8, left: 10, bottom: 60 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" vertical={false} />
              <XAxis dataKey="name" tick={{ fontSize: 9 }} angle={-30} textAnchor="end" interval={0} />
              <YAxis tick={{ fontSize: 10 }} tickFormatter={v => `$${v.toFixed(4)}`} />
              <Tooltip content={<ChartTooltip />} formatter={v => fmtCost(v)} />
              <Bar dataKey="cost" name="Est. Cost ($)" fill="#10b981" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
      <Section
        title="Usage Breakdown"
        onExport={() => exportCSV('llm_cost', cols, rows)}
      >
        <SimpleTable columns={cols} rows={rows} />
      </Section>
    </div>
  )
}

function FeedbackTab({ data }) {
  const rows = data?.bad_feedback || []
  const cols = [
    { key: 'session_id',       label: 'Session', render: r => r.session_id?.slice(0, 8) + '…' },
    { key: 'customer_message', label: 'Customer Message' },
    { key: 'agent_response',   label: 'Bot Answer' },
    { key: 'source',           label: 'Source' },
    { key: 'reason',           label: 'Reason' },
    { key: 'created_at',       label: 'Time', render: r => new Date(r.created_at).toLocaleString() },
  ]
  return (
    <Section
      title={`Negatively Rated Answers (${rows.length})`}
      onExport={() => exportCSV('bad_feedback', cols, rows)}
    >
      <SimpleTable columns={cols} rows={rows} />
    </Section>
  )
}

// ── main ──────────────────────────────────────────────────────────────────────

export default function Reports() {
  const [tab, setTab]         = useState('gaps')
  const [days, setDays]       = useState(30)
  const [channel, setChannel] = useState('')
  const [data, setData]       = useState(null)
  const [loading, setLoading] = useState(true)

  const fetchReports = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({ days })
      if (channel) params.set('channel', channel)
      const res = await fetch(`${api.base}/analytics/reports?${params}`, {
        headers: { Authorization: `Bearer ${api.key}` },
      })
      setData(await res.json())
    } catch (e) {
      console.error(e)
      setData(null)
    } finally {
      setLoading(false)
    }
  }, [days, channel])

  useEffect(() => { fetchReports() }, [fetchReports])

  const channels = data?.channels || []

  const tabContent = {
    gaps:     <GapsTab     data={data} />,
    intents:  <IntentsTab  data={data} />,
    handoffs: <HandoffsTab data={data} />,
    outcomes: <OutcomesTab data={data} />,
    costs:    <CostTab     data={data} />,
    feedback: <FeedbackTab data={data} />,
  }

  return (
    <div className="p-6 max-w-6xl">
      {/* Header */}
      <div className="flex items-center justify-between mb-5 flex-wrap gap-3">
        <h1 className="text-2xl font-bold text-gray-800">Reports</h1>
        <div className="flex items-center gap-2 flex-wrap">
          {/* Channel filter */}
          <select
            value={channel}
            onChange={e => setChannel(e.target.value)}
            className="text-sm border border-gray-200 rounded-lg px-2 py-1.5 bg-white text-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-400"
          >
            <option value="">All channels</option>
            {channels.map(c => (
              <option key={c.channel} value={c.channel}>{c.channel} ({c.messages})</option>
            ))}
          </select>

          {/* Date range */}
          {[7, 30, 90].map(d => (
            <button key={d} onClick={() => setDays(d)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition ${
                days === d ? 'bg-blue-600 text-white' : 'bg-white text-gray-600 border border-gray-200 hover:bg-gray-50'
              }`}>
              {d}d
            </button>
          ))}
          <button
            onClick={fetchReports}
            className="px-3 py-1.5 rounded-lg text-sm bg-white border border-gray-200 hover:bg-gray-50 text-gray-500"
          >
            ↻ Refresh
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-5 bg-gray-100 p-1 rounded-xl w-fit flex-wrap">
        {TABS.map(([id, label]) => (
          <button key={id} onClick={() => setTab(id)}
            className={`px-4 py-1.5 rounded-lg text-sm font-medium transition ${
              tab === id ? 'bg-white text-gray-800 shadow-sm' : 'text-gray-500 hover:text-gray-700'
            }`}>
            {label}
          </button>
        ))}
      </div>

      {loading
        ? <div className="text-center text-gray-400 py-20 text-sm">Loading reports…</div>
        : !data
          ? <div className="text-center text-red-400 py-20 text-sm">Failed to load — check API connection</div>
          : tabContent[tab]
      }
    </div>
  )
}
