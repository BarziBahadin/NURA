import React, { useEffect, useState } from 'react'
import { api } from '../App.jsx'

const TABS = [
  ['gaps', 'Knowledge Gaps'],
  ['intents', 'Intents'],
  ['handoffs', 'Handoffs'],
  ['outcomes', 'Outcomes'],
  ['costs', 'Cost'],
]

function Section({ title, children }) {
  return (
    <div className="bg-white rounded-2xl shadow p-5">
      <h2 className="text-sm font-semibold text-gray-600 uppercase tracking-wide mb-4">{title}</h2>
      {children}
    </div>
  )
}

function Empty() {
  return <div className="text-sm text-gray-400 py-8 text-center">No data for this period</div>
}

function SimpleTable({ columns, rows }) {
  if (!rows?.length) return <Empty />
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-100 text-xs text-gray-400">
            {columns.map(c => <th key={c.key} className="text-left font-medium pb-2">{c.label}</th>)}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} className="border-b border-gray-50">
              {columns.map(c => (
                <td key={c.key} className="py-2 text-gray-700 max-w-md truncate">
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

export default function Reports() {
  const [tab, setTab] = useState('gaps')
  const [days, setDays] = useState(30)
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  async function fetchReports() {
    setLoading(true)
    try {
      const res = await fetch(`${api.base}/analytics/reports?days=${days}`, {
        headers: { Authorization: `Bearer ${api.key}` },
      })
      setData(await res.json())
    } catch (e) {
      console.error(e)
      setData(null)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchReports() }, [days])

  const content = {
    gaps: (
      <Section title="Knowledge Gaps">
        <SimpleTable columns={[
          { key: 'message_text', label: 'Message' },
          { key: 'intent', label: 'Intent' },
          { key: 'sub_intent', label: 'Sub Intent' },
          { key: 'gap_reason', label: 'Reason' },
          { key: 'created_at', label: 'Time', render: r => new Date(r.created_at).toLocaleString() },
        ]} rows={data?.knowledge_gaps || []} />
      </Section>
    ),
    intents: (
      <Section title="Intent Volume">
        <SimpleTable columns={[
          { key: 'intent', label: 'Intent' },
          { key: 'sub_intent', label: 'Sub Intent' },
          { key: 'count', label: 'Count' },
        ]} rows={data?.intents || []} />
      </Section>
    ),
    handoffs: (
      <Section title="Handoff Reasons">
        <SimpleTable columns={[
          { key: 'reason', label: 'Reason' },
          { key: 'count', label: 'Count' },
        ]} rows={data?.handoffs || []} />
      </Section>
    ),
    outcomes: (
      <Section title="Resolution Outcomes">
        <SimpleTable columns={[
          { key: 'status', label: 'Status' },
          { key: 'issue_category', label: 'Category' },
          { key: 'root_cause', label: 'Root Cause' },
          { key: 'count', label: 'Count' },
          { key: 'avg_resolution', label: 'Avg Resolution (s)' },
        ]} rows={data?.outcomes || []} />
      </Section>
    ),
    costs: (
      <Section title="OpenAI Usage & Cost">
        <SimpleTable columns={[
          { key: 'model', label: 'Model' },
          { key: 'operation', label: 'Operation' },
          { key: 'total_tokens', label: 'Tokens' },
          { key: 'estimated_cost', label: 'Est. Cost', render: r => `$${Number(r.estimated_cost || 0).toFixed(6)}` },
        ]} rows={data?.costs || []} />
      </Section>
    ),
  }

  return (
    <div className="p-6 max-w-6xl">
      <div className="flex items-center justify-between mb-5 flex-wrap gap-3">
        <h1 className="text-2xl font-bold text-gray-800">Reports</h1>
        <div className="flex items-center gap-2">
          {[7, 30, 90].map(d => (
            <button key={d} onClick={() => setDays(d)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition ${
                days === d ? 'bg-blue-600 text-white' : 'bg-white text-gray-600 border border-gray-200 hover:bg-gray-50'
              }`}>
              {d}d
            </button>
          ))}
          <button onClick={fetchReports} className="px-3 py-1.5 rounded-lg text-sm bg-white border border-gray-200 hover:bg-gray-50 text-gray-500">
            Refresh
          </button>
        </div>
      </div>
      <div className="flex gap-1 mb-4 bg-gray-100 p-1 rounded-xl w-fit flex-wrap">
        {TABS.map(([id, label]) => (
          <button key={id} onClick={() => setTab(id)}
            className={`px-4 py-1.5 rounded-lg text-sm font-medium transition ${
              tab === id ? 'bg-white text-gray-800 shadow-sm' : 'text-gray-500 hover:text-gray-700'
            }`}>
            {label}
          </button>
        ))}
      </div>
      {loading ? <div className="text-center text-gray-400 py-20 text-sm">Loading reports...</div> : content[tab]}
    </div>
  )
}
