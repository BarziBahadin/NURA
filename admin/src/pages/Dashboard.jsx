import React, { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts'
import {
  ArrowClockwise, Bell, ChartLineUp, ChatCircle, CheckCircle,
  Clock, Cpu, CurrencyDollar, Database, DownloadSimple,
  FirstAidKit, Folder, Info, Lightbulb, MagnifyingGlass,
  PuzzlePiece, Robot, Star, TrendDown,
  TrendUp, UserCircle, Users, Warning, XCircle, ChartBar,
  ChatCenteredText,
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

const SERVICE_ICONS = {
  api: Cpu,
  openai: Robot,
  redis: Database,
  chromadb: MagnifyingGlass,
  postgres: Database,
}

const ICON_TONES = {
  blue:   { bg: 'bg-blue-100',   text: 'text-blue-600',   ring: 'ring-blue-200'   },
  purple: { bg: 'bg-purple-100', text: 'text-purple-600', ring: 'ring-purple-200' },
  red:    { bg: 'bg-red-100',    text: 'text-red-600',    ring: 'ring-red-200'    },
  green:  { bg: 'bg-green-100',  text: 'text-green-600',  ring: 'ring-green-200'  },
  yellow: { bg: 'bg-yellow-100', text: 'text-yellow-600', ring: 'ring-yellow-200' },
  orange: { bg: 'bg-orange-100', text: 'text-orange-600', ring: 'ring-orange-200' },
  indigo: { bg: 'bg-indigo-100', text: 'text-indigo-600', ring: 'ring-indigo-200' },
  gray:   { bg: 'bg-gray-100',   text: 'text-gray-500',   ring: 'ring-gray-200'   },
  teal:   { bg: 'bg-teal-100',   text: 'text-teal-600',   ring: 'ring-teal-200'   },
}

function srcColor(key) { return SOURCE_COLORS[key] || '#6b7280' }
function srcLabel(key) { return SOURCE_LABELS[key] || key }

function formatInt(value) { return Number(value || 0).toLocaleString() }
function formatPercent(value) { return `${Math.round(Number(value || 0) * 100)}%` }
function formatSeconds(value) {
  const s = Math.round(Number(value || 0))
  if (s <= 0) return '0s'
  if (s < 60) return `${s}s`
  if (s < 3600) return `${Math.floor(s / 60)}m`
  return `${Math.floor(s / 3600)}h ${Math.floor((s % 3600) / 60)}m`
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

function SectionCard({ title, children, action, Icon, iconTone = 'blue' }) {
  const tone = ICON_TONES[iconTone] || ICON_TONES.blue
  return (
    <section className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 hover:shadow-md transition-shadow duration-200">
      <div className="flex items-center justify-between gap-3 mb-4">
        <div className="flex items-center gap-2.5">
          {Icon && (
            <span className={`w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 ${tone.bg}`}>
              <Icon size={15} className={tone.text} weight="duotone" />
            </span>
          )}
          <h2 className="text-sm font-semibold text-gray-600 uppercase tracking-wide">{title}</h2>
        </div>
        {action}
      </div>
      {children}
    </section>
  )
}

function NowCard({ label, value, sub, Icon, tone = 'blue', to }) {
  const tones = {
    red:    'border-red-200 bg-gradient-to-br from-red-50 to-red-100/60 text-red-700',
    orange: 'border-orange-200 bg-gradient-to-br from-orange-50 to-orange-100/60 text-orange-700',
    blue:   'border-blue-200 bg-gradient-to-br from-blue-50 to-blue-100/60 text-blue-700',
    green:  'border-green-200 bg-gradient-to-br from-green-50 to-green-100/60 text-green-700',
    gray:   'border-gray-200 bg-white text-gray-700',
  }
  const iconTones = {
    red:    'bg-red-200/70 text-red-600',
    orange: 'bg-orange-200/70 text-orange-600',
    blue:   'bg-blue-200/70 text-blue-600',
    green:  'bg-green-200/70 text-green-600',
    gray:   'bg-gray-200/70 text-gray-600',
  }
  const content = (
    <div className={`border rounded-2xl p-4 h-full transition-all duration-200 ${tones[tone] || tones.blue} ${to ? 'hover:shadow-md hover:scale-[1.01] cursor-pointer' : ''}`}>
      <div className="flex items-start justify-between gap-2 mb-3">
        <div className="text-xs font-semibold uppercase tracking-wide opacity-70 leading-tight">{label}</div>
        <div className={`w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 ${iconTones[tone] || iconTones.blue}`}>
          <Icon size={20} weight="duotone" />
        </div>
      </div>
      <div className="text-3xl font-bold tracking-tight">{value}</div>
      {sub && <div className="text-xs mt-1.5 opacity-60">{sub}</div>}
    </div>
  )
  return to ? <Link to={to}>{content}</Link> : content
}

function DeltaBadge({ delta, inverse = false }) {
  if (!delta) return <span className="text-xs text-gray-300">—</span>
  const percent = Number(delta.percent || 0)
  const isSame = Math.abs(percent) < 0.1
  const positive = percent > 0
  const good = isSame || (inverse ? !positive : positive)
  return (
    <span className={`inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full ${
      isSame ? 'bg-gray-100 text-gray-400' : good ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-600'
    }`}>
      {!isSame && (positive ? <TrendUp size={12} /> : <TrendDown size={12} />)}
      {isSame ? 'same' : `${positive ? '+' : ''}${percent}%`}
    </span>
  )
}

function TrendCard({ label, value, delta, sub, inverse = false, Icon, tone = 'blue' }) {
  const t = ICON_TONES[tone] || ICON_TONES.blue
  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-4 hover:shadow-md transition-all duration-200 group">
      <div className="flex items-start justify-between gap-2 mb-3">
        {Icon ? (
          <div className={`w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 ${t.bg} ring-1 ${t.ring} group-hover:scale-105 transition-transform duration-200`}>
            <Icon size={18} className={t.text} weight="duotone" />
          </div>
        ) : <div />}
        <DeltaBadge delta={delta} inverse={inverse} />
      </div>
      <div className="text-2xl font-bold text-gray-800 tracking-tight">{value}</div>
      <div className="text-xs font-medium text-gray-500 uppercase tracking-wide mt-1">{label}</div>
      {sub && <div className="text-xs text-gray-300 mt-0.5">{sub}</div>}
    </div>
  )
}

const SEVERITY_ICONS = {
  critical: XCircle,
  high: Warning,
  medium: Info,
  info: Info,
}

function ActionItem({ item }) {
  const styles = {
    critical: 'bg-red-50 text-red-700 border-red-100',
    high:     'bg-orange-50 text-orange-700 border-orange-100',
    medium:   'bg-blue-50 text-blue-700 border-blue-100',
    info:     'bg-gray-50 text-gray-600 border-gray-100',
  }[item.severity] || 'bg-gray-50 text-gray-600 border-gray-100'

  const SeverityIcon = SEVERITY_ICONS[item.severity] || Info

  return (
    <Link to={item.path || '/'} className={`block border rounded-xl px-3 py-2 text-sm hover:shadow-sm transition-all duration-150 ${styles}`}>
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <SeverityIcon size={16} weight="duotone" />
          <span className="font-semibold">{item.title}</span>
        </div>
        <span className="text-lg font-bold tabular-nums">{formatInt(item.value)}</span>
      </div>
      {item.detail && <div className="text-xs opacity-70 mt-0.5 ml-6">{item.detail}</div>}
    </Link>
  )
}

function ActionLink({ to, label, value, Icon, tone, disabled }) {
  if (disabled) {
    return (
      <div className="flex items-center gap-3 rounded-xl border border-gray-100 px-3 py-3 opacity-40 cursor-not-allowed">
        <div className="w-9 h-9 rounded-xl flex items-center justify-center bg-gray-100 text-gray-400">
          <Icon size={20} weight="duotone" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="text-sm font-semibold text-gray-400">{label}</div>
          <div className="text-xs text-gray-300">coming soon</div>
        </div>
      </div>
    )
  }
  return (
    <Link to={to} className="flex items-center gap-3 rounded-xl border border-gray-100 px-3 py-3 hover:bg-gray-50 hover:shadow-sm transition-all duration-150 group">
      <div className={`w-9 h-9 rounded-xl flex items-center justify-center transition-transform duration-200 group-hover:scale-105 ${tone}`}>
        <Icon size={20} weight="duotone" />
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
      <div className="flex-1 bg-gray-100 rounded-full h-2">
        <div className="h-2 rounded-full transition-all duration-500" style={{ width: `${pct}%`, background: color }} />
      </div>
      <div className="w-10 text-xs text-gray-500 text-right tabular-nums">{formatInt(count)}</div>
    </div>
  )
}

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-white border border-gray-200 rounded-xl px-3 py-2 shadow-lg text-xs">
      <div className="text-gray-400 mb-1.5 font-medium">{label}</div>
      {payload.map((p, i) => (
        <div key={i} className="flex items-center gap-1.5" style={{ color: p.color || p.fill }}>
          <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: p.color || p.fill }} />
          {p.name}: <strong>{p.value}</strong>
        </div>
      ))}
    </div>
  )
}

function ServiceHealthDot({ status }) {
  if (status === 'ok') return <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse flex-shrink-0" />
  if (status === 'inactive' || status === 'missing') return <span className="w-2 h-2 rounded-full bg-gray-300 flex-shrink-0" />
  return <span className="w-2 h-2 rounded-full bg-red-500 flex-shrink-0" />
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

  const maxTopicClicks = data?.top_tree_topics?.[0]?.clicks || 1
  const maxEventCount = data?.event_breakdown?.[0]?.count || 1
  const maxOwnerCases = data?.cases?.by_owner?.[0]?.count || 1
  const maxChannelSuggestions = data?.suggestions?.by_channel?.[0]?.count || 1

  const allServicesOk = health && Object.values(health.services || {}).every(s => s === 'ok' || s === 'inactive' || s === 'missing')

  return (
    <div className="w-full max-w-none p-6 2xl:p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-bold text-gray-800">Operations Dashboard</h1>
            <span className="flex items-center gap-1.5 text-xs font-semibold text-green-600 bg-green-50 border border-green-100 rounded-full px-2.5 py-0.5">
              <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
              Live
            </span>
          </div>
          {lastUpdated && (
            <div className="text-xs text-gray-400 mt-0.5">
              Updated {secondsAgo < 10 ? 'just now' : `${secondsAgo}s ago`} · auto-refreshes every minute
            </div>
          )}
        </div>
        <div className="flex items-center gap-2">
          {[7, 30, 90].map(d => (
            <button key={d} onClick={() => setDays(d)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all duration-150 ${
                days === d ? 'bg-blue-600 text-white shadow-sm' : 'bg-white text-gray-600 border border-gray-200 hover:bg-gray-50'
              }`}>
              {d}d
            </button>
          ))}
          <button onClick={fetchData}
            className="px-3 py-1.5 rounded-lg text-sm bg-white border border-gray-200 hover:bg-gray-50 text-gray-500 flex items-center gap-1.5 transition-all duration-150">
            <ArrowClockwise size={16} />Refresh
          </button>
        </div>
      </div>

      {loading ? (
        <div className="text-center text-gray-400 py-24 text-sm">
          <div className="w-8 h-8 border-2 border-blue-200 border-t-blue-500 rounded-full animate-spin mx-auto mb-3" />
          Loading operations data…
        </div>
      ) : !data ? (
        <div className="text-center text-red-400 py-24 text-sm">
          <XCircle size={32} className="mx-auto mb-3 text-red-300" weight="duotone" />
          Failed to load data — make sure the API is running
        </div>
      ) : (
        <>
          {/* Needs Attention */}
          <div className="mb-6">
            <div className="flex items-center gap-2 mb-3">
              <Warning size={18} className="text-red-500" weight="fill" />
              <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">Needs Attention</h2>
            </div>
            {(data.attention_items || []).length === 0 ? (
              <div className="flex items-center gap-2.5 bg-green-50 border border-green-100 text-green-700 rounded-2xl px-4 py-3 text-sm">
                <CheckCircle size={18} weight="duotone" className="flex-shrink-0" />
                No urgent operational issues right now. Everything looks good.
              </div>
            ) : (
              <div className="grid grid-cols-[repeat(auto-fit,minmax(260px,1fr))] gap-3">
                {data.attention_items.map(item => <ActionItem key={item.title} item={item} />)}
              </div>
            )}
          </div>

          {/* Live KPI cards */}
          <div className="grid grid-cols-[repeat(auto-fit,minmax(170px,1fr))] 2xl:grid-cols-[repeat(auto-fit,minmax(190px,1fr))] gap-4 mb-6">
            <NowCard label="Pending Handoffs" value={formatInt(data.queue?.pending_handoffs)} sub={`oldest ${formatSeconds(data.queue?.oldest_wait_seconds)}`} Icon={Bell} tone={(data.queue?.pending_handoffs || 0) ? 'orange' : 'green'} to="/queue" />
            <NowCard label="Human Active" value={formatInt(data.queue?.human_active)} sub="live agent chats" Icon={ChatCircle} tone="blue" to="/queue" />
            <NowCard label="Open Cases" value={formatInt(data.cases?.open)} sub={`${formatInt(data.cases?.unassigned)} unassigned`} Icon={Folder} tone={(data.cases?.unassigned || 0) ? 'orange' : 'blue'} to="/cases" />
            <NowCard label="SLA Risk" value={formatInt((data.cases?.breached || 0) + (data.cases?.at_risk || 0))} sub={`${formatInt(data.cases?.breached)} breached`} Icon={FirstAidKit} tone={(data.cases?.breached || 0) ? 'red' : (data.cases?.at_risk || 0) ? 'orange' : 'green'} to="/cases" />
            <NowCard label="Suggestions" value={formatInt(data.suggestions?.new)} sub={`${formatInt(data.suggestions?.unassigned)} unassigned`} Icon={Lightbulb} tone={(data.suggestions?.unassigned || 0) ? 'orange' : 'blue'} to="/suggestions" />
          </div>

          {/* Trend metrics */}
          <div className="mb-6">
            <div className="grid grid-cols-[repeat(auto-fit,minmax(190px,1fr))] gap-4">
              <TrendCard label="Messages" value={formatInt(data.total_messages)} delta={data.deltas?.messages} sub={`last ${days} days`} Icon={ChatCircle} tone="blue" />
              <TrendCard label="Sessions" value={formatInt(data.total_sessions)} delta={data.deltas?.sessions} sub={`${data.total_sessions > 0 ? (data.total_messages / data.total_sessions).toFixed(1) : 0} msg/session`} Icon={Users} tone="purple" />
              <TrendCard label="Escalation" value={formatPercent(data.escalation_rate)} delta={data.deltas?.escalation_rate} sub={`${formatInt(data.escalations)} escalations`} Icon={TrendUp} tone="red" inverse />
              <TrendCard label="Deflection" value={formatPercent(data.deflection_rate)} delta={data.deltas?.deflection_rate} sub="sessions not escalated" Icon={TrendDown} tone="green" />
              <TrendCard label="Feedback" value={formatPercent(data.feedback_positive_rate)} delta={data.deltas?.feedback_positive_rate} sub={`${formatInt(data.feedback_total)} answer votes`} Icon={Star} tone="yellow" />
              <TrendCard label="Today Messages" value={formatInt(data.today?.messages)} delta={data.deltas?.today_messages} sub={`${formatInt(data.today?.sessions)} sessions today`} Icon={ChartLineUp} tone="indigo" />
              <TrendCard label="Avg Rating" value={ratings?.avg_rating != null ? ratings.avg_rating.toFixed(1) : '—'} sub={ratings?.total_rated ? `${ratings.total_rated} ratings` : 'no ratings yet'} Icon={Star} tone="orange" />
              <TrendCard label="AI Cost" value={`$${Number(data.estimated_ai_cost || 0).toFixed(4)}`} sub={`${formatInt(data.llm_total_tokens)} tokens`} Icon={CurrencyDollar} tone="gray" inverse />
            </div>
          </div>

          {/* Action panels */}
          <div className="grid grid-cols-1 xl:grid-cols-2 2xl:grid-cols-4 gap-4 mb-6">
            <SectionCard title="Action Queue" Icon={Bell} iconTone="orange">
              <div className="space-y-2">
                <ActionLink to="/queue" label="Live Queue" value={`${formatInt(data.queue?.pending_handoffs)} waiting`} Icon={Bell} tone="bg-orange-50 text-orange-600" />
                <ActionLink to="/cases" label="Cases" value={`${formatInt(data.cases?.open)} open`} Icon={Folder} tone="bg-blue-50 text-blue-600" />
                <ActionLink to="/suggestions" label="Suggestions" value={`${formatInt(data.suggestions?.unassigned)} unassigned`} Icon={Lightbulb} tone="bg-yellow-50 text-yellow-600" />
                <ActionLink to="/gaps" label="Knowledge Gaps" value={`${formatInt(data.knowledge_gaps)} detected`} Icon={PuzzlePiece} tone="bg-red-50 text-red-600" />
              </div>
            </SectionCard>

            <SectionCard title="Pain Points" Icon={Warning} iconTone="red">
              <div className="space-y-5">
                <div>
                  <div className="text-xs text-gray-400 uppercase tracking-wide mb-2">Top Intents</div>
                  {(data.top_intents || []).length === 0
                    ? <div className="text-xs text-gray-300 py-2 text-center">No intent data</div>
                    : data.top_intents.slice(0, 6).map(row => (
                        <HorizBar key={row.intent} label={row.intent} count={row.count} max={data.top_intents[0]?.count || 1} color="#3b82f6" />
                      ))}
                </div>
                <div>
                  <div className="text-xs text-gray-400 uppercase tracking-wide mb-2">Top Clicked Topics</div>
                  {(data.top_tree_topics || []).length === 0
                    ? <div className="text-xs text-gray-300 py-2 text-center">No topic clicks</div>
                    : data.top_tree_topics.slice(0, 6).map(row => (
                        <HorizBar key={row.topic_id} label={row.topic_label} count={row.clicks} max={maxTopicClicks} color="#ea580c" />
                      ))}
                </div>
              </div>
            </SectionCard>

            <SectionCard title="Workload" Icon={Users} iconTone="indigo">
              <div className="space-y-5">
                <div>
                  <div className="text-xs text-gray-400 uppercase tracking-wide mb-2">Cases By Owner</div>
                  {(data.cases?.by_owner || []).length === 0
                    ? <div className="text-xs text-gray-300 py-2 text-center">No active cases</div>
                    : data.cases.by_owner.map(row => (
                        <HorizBar key={row.owner} label={row.owner} count={row.count} max={maxOwnerCases} color="#0f172a" />
                      ))}
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="rounded-xl bg-blue-50 border border-blue-100 p-3">
                    <div className="flex items-center gap-1.5 text-xs text-blue-500 mb-1">
                      <Clock size={12} weight="duotone" />Avg Queue Wait
                    </div>
                    <div className="text-xl font-bold text-gray-800">{formatSeconds(data.queue?.avg_wait_seconds)}</div>
                  </div>
                  <div className="rounded-xl bg-purple-50 border border-purple-100 p-3">
                    <div className="flex items-center gap-1.5 text-xs text-purple-500 mb-1">
                      <Clock size={12} weight="duotone" />Avg Accept
                    </div>
                    <div className="text-xl font-bold text-gray-800">{formatSeconds(data.avg_time_to_accept_seconds)}</div>
                  </div>
                </div>
              </div>
            </SectionCard>

            <SectionCard title="Channels & Suggestions" Icon={Lightbulb} iconTone="yellow">
              <div className="space-y-5">
                <div>
                  <div className="text-xs text-gray-400 uppercase tracking-wide mb-2">Suggestions By Channel</div>
                  {(data.suggestions?.by_channel || []).length === 0
                    ? <div className="text-xs text-gray-300 py-2 text-center">No suggestions</div>
                    : data.suggestions.by_channel.map(row => (
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

          {/* Charts row */}
          <div className="grid grid-cols-1 xl:grid-cols-3 2xl:grid-cols-4 gap-4 mb-6">
            <div className="xl:col-span-2 2xl:col-span-3">
              <SectionCard title="Daily Traffic" Icon={ChartLineUp} iconTone="blue">
                <ResponsiveContainer width="100%" height={220}>
                  <LineChart data={data.daily_volume || []} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis dataKey="date" tick={{ fontSize: 10 }} tickFormatter={v => String(v).slice(5)} />
                    <YAxis tick={{ fontSize: 10 }} />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend iconSize={10} wrapperStyle={{ fontSize: 11 }} />
                    <Line type="monotone" dataKey="messages" name="Messages" stroke="#3b82f6" strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
                    <Line type="monotone" dataKey="sessions" name="Sessions" stroke="#7c3aed" strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
                  </LineChart>
                </ResponsiveContainer>
              </SectionCard>
            </div>
            <SectionCard title="Response Sources" Icon={ChartBar} iconTone="purple">
              {pieData.length === 0 ? (
                <div className="text-xs text-gray-300 py-8 text-center">No source data</div>
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

          {/* Hourly + health */}
          <div className="grid grid-cols-1 xl:grid-cols-2 2xl:grid-cols-[minmax(0,2fr)_minmax(420px,1fr)] gap-4 mb-6">
            <SectionCard title="Hourly Message Distribution" Icon={Clock} iconTone="indigo">
              <ResponsiveContainer width="100%" height={180}>
                <BarChart data={hourlyData} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" vertical={false} />
                  <XAxis dataKey="hour" tick={{ fontSize: 9 }} interval={3} />
                  <YAxis tick={{ fontSize: 10 }} />
                  <Tooltip content={<CustomTooltip />} />
                  <Bar dataKey="messages" name="Messages" fill="#6366f1" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </SectionCard>

            {health && (
              <SectionCard title="Service Health" Icon={Cpu} iconTone={allServicesOk ? 'green' : 'red'}>
                <div className="grid grid-cols-2 gap-2">
                  {Object.entries(health.services || {}).map(([name, status]) => {
                    const ServiceIcon = SERVICE_ICONS[name] || Cpu
                    const isOk = status === 'ok'
                    const isInactive = status === 'inactive' || status === 'missing'
                    return (
                      <div key={name} className={`flex items-center gap-2.5 rounded-xl px-3 py-2.5 border ${
                        isOk ? 'bg-green-50 border-green-100' : isInactive ? 'bg-gray-50 border-gray-100' : 'bg-red-50 border-red-100'
                      }`}>
                        <ServiceIcon size={15} className={isOk ? 'text-green-500' : isInactive ? 'text-gray-400' : 'text-red-500'} weight="duotone" />
                        <span className="text-xs text-gray-600 flex-1 capitalize">{name.replace('_', ' ')}</span>
                        <ServiceHealthDot status={status} />
                      </div>
                    )
                  })}
                </div>
              </SectionCard>
            )}
          </div>

          {/* Recent conversations */}
          <SectionCard title="Recent Conversations" Icon={ChatCenteredText} iconTone="blue"
            action={
              <button onClick={() => exportCSV(data.recent_conversations || [])}
                className="text-xs bg-gray-100 hover:bg-gray-200 text-gray-600 px-3 py-1.5 rounded-lg transition flex items-center gap-1.5">
                <DownloadSimple size={16} />Export CSV
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
                    <tr key={i} className="border-b border-gray-50 hover:bg-gray-50 transition-colors duration-100">
                      <td className="py-2 font-mono text-xs text-gray-300">{String(r.session_id || '').slice(0, 8)}…</td>
                      <td className="py-2 text-gray-700 max-w-xs truncate">{r.customer_message}</td>
                      <td className="py-2">
                        {r.source ? (
                          <span className="px-2 py-0.5 rounded-full text-xs font-medium"
                            style={{ background: srcColor(r.source) + '20', color: srcColor(r.source) }}>
                            {srcLabel(r.source)}
                          </span>
                        ) : <span className="text-gray-200">—</span>}
                      </td>
                      <td className="py-2 text-xs font-semibold tabular-nums"
                        style={{ color: r.confidence >= 0.8 ? '#16a34a' : r.confidence >= 0.5 ? '#ca8a04' : '#dc2626' }}>
                        {Math.round((r.confidence || 0) * 100)}%
                      </td>
                      <td className="py-2">
                        {r.escalated
                          ? <span className="bg-red-100 text-red-600 text-xs px-2 py-0.5 rounded-full font-medium">Escalated</span>
                          : <span className="bg-green-100 text-green-700 text-xs px-2 py-0.5 rounded-full font-medium">Automated</span>}
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
