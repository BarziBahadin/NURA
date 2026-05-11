import React, { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts'
import {
  ArrowClockwise, Bell, ChartLineUp, ChatCircle, DownloadSimple,
  FirstAidKit, Folder, Lightbulb, PhoneCall, PuzzlePiece, Star, TrendDown,
  TrendUp, UserCircle, Warning,
} from '@phosphor-icons/react'
import { api } from '../App.jsx'

const SOURCE_COLORS = {
  openai: '#7c3aed',
  rag: '#10b981',
  rules: '#f59e0b',
  local_model: '#0d9488',
  'rule-based': '#f59e0b',
  escalated: '#ef4444',
}

const SOURCE_LABELS = {
  openai: 'AI (OpenAI)',
  rag: 'RAG',
  rules: 'Rules',
  local_model: 'ML',
  'rule-based': 'Rules',
  escalated: 'Escalated',
}

const EVENT_LABELS = {
  chat_open: 'Chat Opened',
  chat_close: 'Chat Closed',
  send_message: 'Message Sent',
  lang_switch: 'Language Switch',
  tree_click: 'Tree Topic',
  tree_back: 'Tree Back',
  tree_home: 'Tree Home',
  followup_yes: 'Follow-up: Yes',
  followup_no: 'Follow-up: No',
  feedback_good: 'Feedback: Good',
  feedback_bad: 'Feedback: Bad',
  suggestion_open: 'Suggestion Opened',
  suggestion_submit: 'Suggestion Submitted',
}

function srcColor(key) { return SOURCE_COLORS[key] || '#6b7280' }
function srcLabel(key) { return SOURCE_LABELS[key] || key }

function formatInt(value) {
  return Number(value || 0).toLocaleString()
}

function formatPercent(value) {
  return `${Math.round(Number(value || 0) * 100)}%`
}

function formatSeconds(value) {
  const seconds = Math.round(Number(value || 0))
  if (seconds <= 0) return '0s'
  if (seconds < 60) return `${seconds}s`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`
  return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`
}

function exportCSV(rows) {
  const headers = ['session_id', 'channel', 'customer_message', 'source', 'confidence', 'escalated', 'created_at']
  const lines = [headers.join(','), ...rows.map(r => headers.map(h => JSON.stringify(r[h] ?? '')).join(','))]
  const a = Object.assign(document.createElement('a'), {
    href: URL.createObjectURL(new Blob([lines.join('\n')], { type: 'text/csv' })),
    download: `nura_${new Date().toISOString().slice(0, 10)}.csv`,
  })
  a.click()
}

function SectionCard({ title, children, action }) {
  return (
    <section className="bg-white rounded-2xl shadow p-5">
      <div className="flex items-center justify-between gap-3 mb-4">
        <h2 className="text-sm font-semibold text-gray-600 uppercase tracking-wide">{title}</h2>
        {action}
      </div>
      {children}
    </section>
  )
}

function NowCard({ label, value, sub, Icon, tone = 'blue', to }) {
  const tones = {
    red: 'border-red-200 bg-red-50 text-red-700',
    orange: 'border-orange-200 bg-orange-50 text-orange-700',
    blue: 'border-blue-200 bg-blue-50 text-blue-700',
    green: 'border-green-200 bg-green-50 text-green-700',
    gray: 'border-gray-200 bg-white text-gray-700',
  }
  const content = (
    <div className={`border rounded-2xl p-4 h-full transition ${tones[tone] || tones.blue} ${to ? 'hover:shadow-md' : ''}`}>
      <div className="flex items-center justify-between gap-3">
        <div className="text-xs font-semibold uppercase tracking-wide opacity-75">{label}</div>
        <Icon size={24} />
      </div>
      <div className="text-3xl font-bold mt-3">{value}</div>
      {sub && <div className="text-xs mt-1 opacity-75">{sub}</div>}
    </div>
  )
  return to ? <Link to={to}>{content}</Link> : content
}

function DeltaBadge({ delta, inverse = false }) {
  if (!delta) return <span className="text-xs text-gray-400">same</span>
  const percent = Number(delta.percent || 0)
  const isSame = Math.abs(percent) < 0.1
  const positive = percent > 0
  const good = isSame || (inverse ? !positive : positive)
  return (
    <span className={`inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full ${
      isSame ? 'bg-gray-100 text-gray-500' : good ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
    }`}>
      {!isSame && (positive ? <TrendUp size={14} /> : <TrendDown size={14} />)}
      {isSame ? 'same' : `${positive ? '+' : ''}${percent}%`}
    </span>
  )
}

function TrendCard({ label, value, delta, sub, inverse = false }) {
  return (
    <div className="bg-white rounded-2xl shadow p-4">
      <div className="flex items-center justify-between gap-2 mb-2">
        <div className="text-xs text-gray-400 uppercase tracking-wide">{label}</div>
        <DeltaBadge delta={delta} inverse={inverse} />
      </div>
      <div className="text-2xl font-bold text-gray-800">{value}</div>
      {sub && <div className="text-xs text-gray-400 mt-1">{sub}</div>}
    </div>
  )
}

function ActionItem({ item }) {
  const tone = {
    critical: 'bg-red-50 text-red-700 border-red-100',
    high: 'bg-orange-50 text-orange-700 border-orange-100',
    medium: 'bg-blue-50 text-blue-700 border-blue-100',
    info: 'bg-gray-50 text-gray-600 border-gray-100',
  }[item.severity] || 'bg-gray-50 text-gray-600 border-gray-100'

  return (
    <Link to={item.path || '/'} className={`block border rounded-xl px-3 py-2 text-sm hover:shadow-sm transition ${tone}`}>
      <div className="flex items-center justify-between gap-3">
        <span className="font-semibold">{item.title}</span>
        <span className="text-lg font-bold">{formatInt(item.value)}</span>
      </div>
      {item.detail && <div className="text-xs opacity-75 mt-0.5">{item.detail}</div>}
    </Link>
  )
}

function ActionLink({ to, label, value, Icon, tone }) {
  return (
    <Link to={to} className="flex items-center gap-3 rounded-xl border border-gray-100 px-3 py-3 hover:bg-gray-50 transition">
      <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${tone}`}>
        <Icon size={22} />
      </div>
      <div className="min-w-0 flex-1">
        <div className="text-sm font-semibold text-gray-700">{label}</div>
        <div className="text-xs text-gray-400">{value}</div>
      </div>
    </Link>
  )
}

function HorizBar({ label, count, max, color }) {
  const pct = max > 0 ? Math.round((Number(count || 0) / max) * 100) : 0
  return (
    <div className="flex items-center gap-3 mb-2">
      <div className="w-36 text-xs text-gray-500 truncate">{label || 'unknown'}</div>
      <div className="flex-1 bg-gray-100 rounded-full h-2.5">
        <div className="h-2.5 rounded-full transition-all" style={{ width: `${pct}%`, background: color }} />
      </div>
      <div className="w-10 text-xs text-gray-500 text-right">{formatInt(count)}</div>
    </div>
  )
}

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-white border border-gray-200 rounded-xl px-3 py-2 shadow text-xs">
      <div className="text-gray-500 mb-1">{label}</div>
      {payload.map((p, i) => (
        <div key={i} style={{ color: p.color || p.fill }}>{p.name}: <strong>{p.value}</strong></div>
      ))}
    </div>
  )
}

export default function Dashboard() {
  const [data, setData] = useState(null)
  const [health, setHealth] = useState(null)
  const [ratings, setRatings] = useState(null)
  const [days, setDays] = useState(30)
  const [loading, setLoading] = useState(true)
  const [lastUpdated, setLastUpdated] = useState(null)
  const [secondsAgo, setSecondsAgo] = useState(0)

  const fetchData = useCallback(async () => {
    try {
      const h = { Authorization: `Bearer ${api.key}` }
      const [analytics, healthData, ratingsData] = await Promise.all([
        fetch(`${api.base}/analytics/dashboard?days=${days}`, { headers: h }).then(r => r.json()),
        fetch(`${api.base}/health`, { headers: h }).then(r => r.json()),
        fetch(`${api.base}/analytics/ratings`, { headers: h }).then(r => r.json()),
      ])
      setData(analytics)
      setHealth(healthData)
      setRatings(ratingsData)
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

  const hourlyData = data
    ? Array.from({ length: 24 }, (_, displayHour) => {
        const utcHour = (displayHour - 3 + 24) % 24
        return {
          hour: `${displayHour}:00`,
          messages: (data.hourly_distribution || []).find(r => r.hour === utcHour)?.messages || 0,
        }
      })
    : []

  const pieData = data
    ? Object.entries(data.source_breakdown || {}).map(([key, value]) => ({
        name: srcLabel(key), value, color: srcColor(key),
      }))
    : []

  const totalClicks = data?.top_tree_topics?.reduce((s, t) => s + t.clicks, 0) || 0
  const maxTopicClicks = data?.top_tree_topics?.[0]?.clicks || 1
  const maxEventCount = data?.event_breakdown?.[0]?.count || 1
  const maxOwnerCases = data?.cases?.by_owner?.[0]?.count || 1
  const maxChannelSuggestions = data?.suggestions?.by_channel?.[0]?.count || 1

  return (
    <div className="w-full max-w-none p-6 2xl:p-8">
      <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Operations Dashboard</h1>
          {lastUpdated && (
            <div className="text-xs text-gray-400 mt-0.5">
              Last updated: {secondsAgo < 10 ? 'just now' : `${secondsAgo}s ago`} - auto-refreshes every minute
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
            className="px-3 py-1.5 rounded-lg text-sm bg-white border border-gray-200 hover:bg-gray-50 text-gray-500 flex items-center gap-1.5">
            <ArrowClockwise size={18} />Refresh
          </button>
        </div>
      </div>

      {loading ? (
        <div className="text-center text-gray-400 py-20 text-sm">Loading operations data...</div>
      ) : !data ? (
        <div className="text-center text-red-400 py-20 text-sm">Failed to load data - make sure the API is running</div>
      ) : (
        <>
          <div className="mb-6">
            <div className="flex items-center gap-2 mb-3">
              <Warning size={20} className="text-red-500" weight="fill" />
              <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">Needs Attention</h2>
            </div>
            {(data.attention_items || []).length === 0 ? (
              <div className="bg-green-50 border border-green-100 text-green-700 rounded-2xl px-4 py-3 text-sm">
                No urgent operational issues right now.
              </div>
            ) : (
              <div className="grid grid-cols-[repeat(auto-fit,minmax(260px,1fr))] gap-3">
                {data.attention_items.map(item => <ActionItem key={item.title} item={item} />)}
              </div>
            )}
          </div>

          <div className="grid grid-cols-[repeat(auto-fit,minmax(170px,1fr))] 2xl:grid-cols-[repeat(auto-fit,minmax(190px,1fr))] gap-4 mb-6">
            <NowCard label="Pending Handoffs" value={formatInt(data.queue?.pending_handoffs)} sub={`oldest ${formatSeconds(data.queue?.oldest_wait_seconds)}`} Icon={Bell} tone={(data.queue?.pending_handoffs || 0) ? 'orange' : 'green'} to="/queue" />
            <NowCard label="Human Active" value={formatInt(data.queue?.human_active)} sub="live agent chats" Icon={ChatCircle} tone="blue" to="/queue" />
            <NowCard label="Voice Calls" value={formatInt(data.voice_calls?.open)} sub={`${formatInt(data.voice_calls?.requested)} waiting`} Icon={PhoneCall} tone={(data.voice_calls?.requested || 0) ? 'orange' : (data.voice_calls?.open || 0) ? 'blue' : 'green'} to="/calls" />
            <NowCard label="Open Cases" value={formatInt(data.cases?.open)} sub={`${formatInt(data.cases?.unassigned)} unassigned`} Icon={Folder} tone={(data.cases?.unassigned || 0) ? 'orange' : 'blue'} to="/cases" />
            <NowCard label="SLA Risk" value={formatInt((data.cases?.breached || 0) + (data.cases?.at_risk || 0))} sub={`${formatInt(data.cases?.breached)} breached`} Icon={FirstAidKit} tone={(data.cases?.breached || 0) ? 'red' : (data.cases?.at_risk || 0) ? 'orange' : 'green'} to="/cases" />
            <NowCard label="Suggestions" value={formatInt(data.suggestions?.new)} sub={`${formatInt(data.suggestions?.unassigned)} unassigned`} Icon={Lightbulb} tone={(data.suggestions?.unassigned || 0) ? 'orange' : 'blue'} to="/suggestions" />
          </div>

          <div className="mb-6">
            <div className="grid grid-cols-[repeat(auto-fit,minmax(190px,1fr))] gap-4">
              <TrendCard label="Messages" value={formatInt(data.total_messages)} delta={data.deltas?.messages} sub={`last ${days} days`} />
              <TrendCard label="Sessions" value={formatInt(data.total_sessions)} delta={data.deltas?.sessions} sub={`${data.total_sessions > 0 ? (data.total_messages / data.total_sessions).toFixed(1) : 0} msg/session`} />
              <TrendCard label="Escalation" value={formatPercent(data.escalation_rate)} delta={data.deltas?.escalation_rate} sub={`${formatInt(data.escalations)} escalations`} inverse />
              <TrendCard label="Deflection" value={formatPercent(data.deflection_rate)} delta={data.deltas?.deflection_rate} sub="sessions not escalated" />
              <TrendCard label="Feedback" value={formatPercent(data.feedback_positive_rate)} delta={data.deltas?.feedback_positive_rate} sub={`${formatInt(data.feedback_total)} answer votes`} />
              <TrendCard label="Today Messages" value={formatInt(data.today?.messages)} delta={data.deltas?.today_messages} sub={`${formatInt(data.today?.sessions)} sessions today`} />
              <TrendCard label="Avg Rating" value={ratings?.avg_rating != null ? ratings.avg_rating.toFixed(1) : '-'} sub={ratings?.total_rated ? `${ratings.total_rated} ratings` : 'no ratings yet'} />
              <TrendCard label="AI Cost" value={`$${Number(data.estimated_ai_cost || 0).toFixed(4)}`} sub={`${formatInt(data.llm_total_tokens)} tokens`} inverse />
            </div>
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-2 2xl:grid-cols-4 gap-4 mb-6">
            <SectionCard title="Action Queue">
              <div className="space-y-2">
                <ActionLink to="/queue" label="Live Queue" value={`${formatInt(data.queue?.pending_handoffs)} waiting`} Icon={Bell} tone="bg-orange-50 text-orange-600" />
                <ActionLink to="/calls" label="Call Desk" value={`${formatInt(data.voice_calls?.open)} open`} Icon={PhoneCall} tone="bg-orange-50 text-orange-600" />
                <ActionLink to="/cases" label="Cases" value={`${formatInt(data.cases?.open)} open`} Icon={Folder} tone="bg-blue-50 text-blue-600" />
                <ActionLink to="/suggestions" label="Suggestions" value={`${formatInt(data.suggestions?.unassigned)} unassigned`} Icon={Lightbulb} tone="bg-yellow-50 text-yellow-600" />
                <ActionLink to="/gaps" label="Knowledge Gaps" value={`${formatInt(data.knowledge_gaps)} detected`} Icon={PuzzlePiece} tone="bg-red-50 text-red-600" />
              </div>
            </SectionCard>

            <SectionCard title="Pain Points">
              <div className="space-y-5">
                <div>
                  <div className="text-xs text-gray-400 uppercase tracking-wide mb-2">Top Intents</div>
                  {(data.top_intents || []).length === 0 ? <div className="text-xs text-gray-400">No intent data</div> : data.top_intents.slice(0, 6).map(row => (
                    <HorizBar key={row.intent} label={row.intent} count={row.count} max={data.top_intents[0]?.count || 1} color="#3b82f6" />
                  ))}
                </div>
                <div>
                  <div className="text-xs text-gray-400 uppercase tracking-wide mb-2">Top Clicked Topics</div>
                  {(data.top_tree_topics || []).length === 0 ? <div className="text-xs text-gray-400">No topic clicks</div> : data.top_tree_topics.slice(0, 6).map(row => (
                    <HorizBar key={row.topic_id} label={row.topic_label} count={row.clicks} max={maxTopicClicks} color="#ea580c" />
                  ))}
                </div>
              </div>
            </SectionCard>

            <SectionCard title="Workload">
              <div className="space-y-5">
                <div>
                  <div className="text-xs text-gray-400 uppercase tracking-wide mb-2">Cases By Owner</div>
                  {(data.cases?.by_owner || []).length === 0 ? <div className="text-xs text-gray-400">No active cases</div> : data.cases.by_owner.map(row => (
                    <HorizBar key={row.owner} label={row.owner} count={row.count} max={maxOwnerCases} color="#0f172a" />
                  ))}
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="rounded-xl bg-gray-50 p-3">
                    <div className="text-xs text-gray-400">Avg Queue Wait</div>
                    <div className="text-xl font-bold text-gray-800">{formatSeconds(data.queue?.avg_wait_seconds)}</div>
                  </div>
                  <div className="rounded-xl bg-gray-50 p-3">
                    <div className="text-xs text-gray-400">Avg Accept</div>
                    <div className="text-xl font-bold text-gray-800">{formatSeconds(data.avg_time_to_accept_seconds)}</div>
                  </div>
                </div>
              </div>
            </SectionCard>

            <SectionCard title="Channels & Suggestions">
              <div className="space-y-5">
                <div>
                  <div className="text-xs text-gray-400 uppercase tracking-wide mb-2">Suggestions By Channel</div>
                  {(data.suggestions?.by_channel || []).length === 0 ? <div className="text-xs text-gray-400">No suggestions</div> : data.suggestions.by_channel.map(row => (
                    <HorizBar key={row.channel} label={row.channel} count={row.count} max={maxChannelSuggestions} color="#ca8a04" />
                  ))}
                </div>
                <div>
                  <div className="text-xs text-gray-400 uppercase tracking-wide mb-2">Widget Interactions</div>
                  {(data.event_breakdown || []).slice(0, 5).map(row => (
                    <HorizBar key={row.event_type} label={EVENT_LABELS[row.event_type] || row.event_type} count={row.count} max={maxEventCount} color="#7c3aed" />
                  ))}
                </div>
              </div>
            </SectionCard>
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-3 2xl:grid-cols-4 gap-4 mb-6">
            <div className="xl:col-span-2 2xl:col-span-3">
              <SectionCard title="Daily Traffic">
                <ResponsiveContainer width="100%" height={220}>
                  <LineChart data={data.daily_volume || []} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis dataKey="date" tick={{ fontSize: 10 }} tickFormatter={v => String(v).slice(5)} />
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
                    <Pie data={pieData} cx="50%" cy="45%" innerRadius={55} outerRadius={85} paddingAngle={3} dataKey="value">
                      {pieData.map((entry, i) => <Cell key={i} fill={entry.color} />)}
                    </Pie>
                    <Tooltip formatter={(v, n) => [`${v} messages`, n]} />
                    <Legend iconSize={10} wrapperStyle={{ fontSize: 11 }} />
                  </PieChart>
                </ResponsiveContainer>
              )}
            </SectionCard>
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-2 2xl:grid-cols-[minmax(0,2fr)_minmax(420px,1fr)] gap-4 mb-6">
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
            </SectionCard>

            {health && (
              <SectionCard title="Service Health">
                <div className="grid grid-cols-2 gap-2">
                  {Object.entries(health.services || {}).map(([name, status]) => (
                    <div key={name} className="flex items-center gap-2 bg-gray-50 rounded-xl px-3 py-2">
                      <span className={`w-2 h-2 rounded-full flex-shrink-0 ${status === 'ok' ? 'bg-green-400 animate-pulse' : status === 'inactive' || status === 'missing' ? 'bg-gray-400' : 'bg-red-500'}`} />
                      <span className="text-xs text-gray-600 flex-1">{name.replace('_', ' ')}</span>
                      <span className={`text-xs ${status === 'ok' ? 'text-green-500' : status === 'inactive' || status === 'missing' ? 'text-gray-400' : 'text-red-500'}`}>{status}</span>
                    </div>
                  ))}
                </div>
              </SectionCard>
            )}
          </div>

          <SectionCard title="Recent Conversations"
            action={
              <button onClick={() => exportCSV(data.recent_conversations || [])}
                className="text-xs bg-gray-100 hover:bg-gray-200 text-gray-600 px-3 py-1.5 rounded-lg transition flex items-center gap-1.5">
                <DownloadSimple size={18} />Export CSV
              </button>
            }>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-100 text-xs text-gray-400">
                    {['Session', 'Message', 'Source', 'Confidence', 'Status', 'Time'].map(h => (
                      <th key={h} className="pb-2 text-left font-medium">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(data.recent_conversations || []).slice(0, 12).map((r, i) => (
                    <tr key={i} className="border-b border-gray-50 hover:bg-gray-50 transition">
                      <td className="py-2 font-mono text-xs text-gray-400">{String(r.session_id || '').slice(0, 8)}...</td>
                      <td className="py-2 text-gray-700 max-w-xs truncate">{r.customer_message}</td>
                      <td className="py-2">
                        {r.source ? (
                          <span className="px-2 py-0.5 rounded-full text-xs font-medium"
                            style={{ background: srcColor(r.source) + '20', color: srcColor(r.source) }}>
                            {srcLabel(r.source)}
                          </span>
                        ) : <span className="text-gray-300">-</span>}
                      </td>
                      <td className="py-2 text-xs font-medium"
                        style={{ color: r.confidence >= 0.8 ? '#16a34a' : r.confidence >= 0.5 ? '#ca8a04' : '#dc2626' }}>
                        {Math.round((r.confidence || 0) * 100)}%
                      </td>
                      <td className="py-2">
                        {r.escalated
                          ? <span className="bg-red-100 text-red-600 text-xs px-2 py-0.5 rounded-full">Escalated</span>
                          : <span className="bg-green-100 text-green-600 text-xs px-2 py-0.5 rounded-full">Automated</span>}
                      </td>
                      <td className="py-2 text-xs text-gray-400 whitespace-nowrap">
                        {new Date(r.created_at).toLocaleDateString('en', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
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
