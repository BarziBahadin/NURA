import React, { useCallback, useEffect, useState } from 'react'
import { ArrowClockwise, CheckCircle, Clock, GitBranch, Lightbulb, UserCircle } from '@phosphor-icons/react'
import Cases from './Cases.jsx'
import { api } from '../App.jsx'

function StatCard({ label, value, Icon, tone = 'text-gray-800', sub }) {
  return (
    <div className="bg-white rounded-xl shadow px-4 py-3 flex items-center gap-3">
      <div className="w-10 h-10 rounded-lg bg-gray-50 flex items-center justify-center">
        <Icon size={24} className={tone} />
      </div>
      <div>
        <div className="text-xs text-gray-400 uppercase tracking-wide">{label}</div>
        <div className={`text-2xl font-bold ${tone}`}>{value ?? '—'}</div>
        {sub && <div className="text-xs text-gray-400">{sub}</div>}
      </div>
    </div>
  )
}

function ChannelPill({ item }) {
  return (
    <div className="flex items-center justify-between gap-3 text-sm">
      <span className="text-gray-600 capitalize">{item.channel}</span>
      <span className="font-semibold text-gray-800">{item.count}</span>
    </div>
  )
}

export default function Suggestions() {
  const [stats, setStats] = useState(null)
  const [error, setError] = useState('')

  const fetchStats = useCallback(async () => {
    setError('')
    try {
      const res = await fetch(`${api.base}/suggestions/stats`, {
        headers: { Authorization: `Bearer ${api.key}` },
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(data.detail || 'Failed to load suggestion stats')
      setStats(data)
    } catch (e) {
      setError(e.message)
    }
  }, [])

  useEffect(() => {
    fetchStats()
    const t = setInterval(fetchStats, 15000)
    return () => clearInterval(t)
  }, [fetchStats])

  return (
    <div>
      <div className="p-6 max-w-7xl mx-auto w-full pb-0">
        <div className="flex items-center justify-between gap-3 flex-wrap mb-5">
          <div>
            <h1 className="text-2xl font-bold text-gray-800">Suggestions</h1>
            <div className="text-xs text-gray-400 mt-1">
              Review complaints, recommendations, and product feedback from web and Telegram.
            </div>
          </div>
          <button onClick={fetchStats} className="px-3 py-2 rounded-xl bg-white border border-gray-200 text-sm text-gray-600 hover:bg-gray-50 flex items-center gap-2">
            <ArrowClockwise size={18} /> Refresh
          </button>
        </div>

        {error && <div className="mb-4 bg-red-50 border border-red-100 text-red-700 rounded-xl px-4 py-3 text-sm">{error}</div>}

        <div className="grid grid-cols-2 lg:grid-cols-5 gap-4 mb-5">
          <StatCard label="New" value={stats?.new} Icon={Lightbulb} tone={(stats?.new || 0) ? 'text-blue-600' : 'text-gray-500'} />
          <StatCard label="Reviewed" value={stats?.reviewed} Icon={Clock} tone="text-indigo-600" />
          <StatCard label="Converted" value={stats?.converted} Icon={GitBranch} tone="text-orange-600" sub="Escalated cases" />
          <StatCard label="Closed" value={stats?.closed} Icon={CheckCircle} tone="text-green-600" />
          <StatCard label="Unassigned" value={stats?.unassigned} Icon={UserCircle} tone={(stats?.unassigned || 0) ? 'text-red-600' : 'text-gray-500'} />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-2">
          <div className="bg-white rounded-xl shadow p-4">
            <div className="text-xs text-gray-400 uppercase tracking-wide mb-3">Workflow</div>
            <div className="grid grid-cols-2 gap-2 text-xs text-gray-500">
              <div className="border border-gray-100 rounded-lg p-2"><span className="font-semibold text-gray-800">Open</span> means new inbox item.</div>
              <div className="border border-gray-100 rounded-lg p-2"><span className="font-semibold text-gray-800">In Progress</span> means reviewed.</div>
              <div className="border border-gray-100 rounded-lg p-2"><span className="font-semibold text-gray-800">Escalated</span> means converted to action.</div>
              <div className="border border-gray-100 rounded-lg p-2"><span className="font-semibold text-gray-800">Resolved</span> means closed out.</div>
            </div>
          </div>
          <div className="bg-white rounded-xl shadow p-4">
            <div className="text-xs text-gray-400 uppercase tracking-wide mb-3">Channels</div>
            <div className="space-y-2">
              {(stats?.by_channel || []).length === 0 ? (
                <div className="text-sm text-gray-400">No submissions yet</div>
              ) : (
                stats.by_channel.map(item => <ChannelPill key={item.channel} item={item} />)
              )}
            </div>
          </div>
          <div className="bg-white rounded-xl shadow p-4">
            <div className="text-xs text-gray-400 uppercase tracking-wide mb-3">Last 14 Days</div>
            <div className="flex items-end gap-1 h-20">
              {(stats?.daily || []).map(day => {
                const max = Math.max(1, ...(stats?.daily || []).map(d => d.count))
                return (
                  <div key={day.day} className="flex-1 bg-blue-100 rounded-t" title={`${day.day}: ${day.count}`}
                    style={{ height: `${Math.max(8, (day.count / max) * 80)}px` }} />
                )
              })}
            </div>
          </div>
        </div>
      </div>

      <Cases
        initialDepartment="suggestions"
        title="Suggestion Inbox"
        subtitle="Assign, review, convert, and close customer suggestions without mixing them into the general case queue."
        createLabel="New Suggestion Case"
        hideDepartmentFilter
        embeddedHeader
      />
    </div>
  )
}
