import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { api } from '../App.jsx'
import { getUsername } from '../lib/api.js'

const STATUSES = [
  ['all', 'All'],
  ['open', 'Open'],
  ['in_progress', 'In Progress'],
  ['waiting_customer', 'Waiting Customer'],
  ['escalated', 'Escalated'],
  ['pending', 'Pending'],
  ['resolved', 'Resolved'],
  ['closed', 'Closed'],
]

const PRIORITIES = [
  ['all', 'All'],
  ['urgent', 'Urgent'],
  ['high', 'High'],
  ['normal', 'Normal'],
  ['low', 'Low'],
]

const MUTABLE_STATUSES = STATUSES.filter(([v]) => v !== 'all')
const MUTABLE_PRIORITIES = PRIORITIES.filter(([v]) => v !== 'all')

const STATUS_STYLE = {
  open: 'bg-blue-50 text-blue-700 border-blue-100',
  pending: 'bg-gray-50 text-gray-600 border-gray-100',
  in_progress: 'bg-indigo-50 text-indigo-700 border-indigo-100',
  waiting_customer: 'bg-amber-50 text-amber-700 border-amber-100',
  escalated: 'bg-red-50 text-red-700 border-red-100',
  resolved: 'bg-green-50 text-green-700 border-green-100',
  closed: 'bg-slate-100 text-slate-600 border-slate-200',
}

const PRIORITY_STYLE = {
  urgent: 'text-red-700 bg-red-50 border-red-100',
  high: 'text-orange-700 bg-orange-50 border-orange-100',
  normal: 'text-blue-700 bg-blue-50 border-blue-100',
  low: 'text-gray-600 bg-gray-50 border-gray-100',
}

function labelFor(items, value) {
  return items.find(([v]) => v === value)?.[1] || value || 'Unassigned'
}

function formatTime(value) {
  if (!value) return 'Not set'
  return new Date(value).toLocaleString()
}

function timeState(value, status) {
  if (!value || ['resolved', 'closed'].includes(status)) return { label: 'No active SLA', tone: 'text-gray-400' }
  const due = new Date(value).getTime()
  const now = Date.now()
  const diff = due - now
  if (diff < 0) return { label: 'Overdue', tone: 'text-red-600' }
  const hours = Math.round(diff / 36e5)
  if (hours <= 2) return { label: `Due in ${Math.max(1, hours)}h`, tone: 'text-orange-600' }
  if (hours < 24) return { label: `Due in ${hours}h`, tone: 'text-amber-600' }
  return { label: `Due in ${Math.round(hours / 24)}d`, tone: 'text-gray-500' }
}

function slaTone(status) {
  if (status === 'breached') return 'text-red-600'
  if (status === 'at_risk') return 'text-orange-600'
  return 'text-gray-500'
}

function Kpi({ label, value, tone = 'text-gray-800' }) {
  return (
    <div className="bg-white rounded-2xl shadow p-4">
      <div className="text-xs text-gray-400 uppercase tracking-wide mb-1">{label}</div>
      <div className={`text-2xl font-bold ${tone}`}>{value}</div>
    </div>
  )
}

function activityText(item) {
  if (item.action === 'created') return item.note || 'Case created'
  if (item.action === 'note_added') return item.note || 'Note added'
  if (item.action === 'field_changed') {
    return `${item.field_name} changed from "${item.old_value || 'empty'}" to "${item.new_value || 'empty'}"`
  }
  if (item.action === 'handoff_linked') return item.note || 'Handoff linked to existing case'
  if (item.action === 'session_case_reused') return `Existing active case reused for session ${item.note || ''}`
  return item.note || item.action
}

function CreateCaseModal({ departments, onClose, onCreated }) {
  const [form, setForm] = useState({
    title: '',
    description: '',
    department: 'general',
    priority: 'normal',
    owner: getUsername() || '',
    channel: 'web',
    customer_id: '',
    session_id: '',
    internal_notes: '',
    tags: '',
  })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  function set(name, value) {
    setForm(f => ({ ...f, [name]: value }))
  }

  async function submit(e) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      const payload = {
        ...form,
        customer_id: form.customer_id || null,
        session_id: form.session_id || null,
        owner: form.owner || null,
        tags: form.tags.split(',').map(t => t.trim()).filter(Boolean),
      }
      const res = await fetch(`${api.base}/cases`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${api.key}`, 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(data.detail || 'Failed to create case')
      onCreated(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
      <form onSubmit={submit} className="bg-white rounded-2xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="p-5 border-b border-gray-100 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-gray-800">Create Case</h2>
            <div className="text-xs text-gray-400 mt-1">Manual support case without customer profile dependency</div>
          </div>
          <button type="button" onClick={onClose} className="text-gray-400 hover:text-gray-700 text-xl">×</button>
        </div>

        <div className="p-5 space-y-4">
          {error && <div className="bg-red-50 border border-red-100 text-red-700 rounded-xl px-3 py-2 text-sm">{error}</div>}

          <div>
            <label className="text-xs font-semibold text-gray-500">Title</label>
            <input required value={form.title} onChange={e => set('title', e.target.value)}
              className="mt-1 w-full border border-gray-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-400" />
          </div>

          <div>
            <label className="text-xs font-semibold text-gray-500">Description</label>
            <textarea value={form.description} onChange={e => set('description', e.target.value)} rows={4}
              className="mt-1 w-full border border-gray-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-400" />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="text-xs font-semibold text-gray-500">Department</label>
              <select value={form.department} onChange={e => set('department', e.target.value)}
                className="mt-1 w-full border border-gray-200 rounded-xl px-3 py-2 text-sm bg-white">
                {departments.map(d => <option key={d.code} value={d.code}>{d.name}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs font-semibold text-gray-500">Priority</label>
              <select value={form.priority} onChange={e => set('priority', e.target.value)}
                className="mt-1 w-full border border-gray-200 rounded-xl px-3 py-2 text-sm bg-white">
                {MUTABLE_PRIORITIES.map(([v, label]) => <option key={v} value={v}>{label}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs font-semibold text-gray-500">Owner</label>
              <input value={form.owner} onChange={e => set('owner', e.target.value)}
                className="mt-1 w-full border border-gray-200 rounded-xl px-3 py-2 text-sm" />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="text-xs font-semibold text-gray-500">Channel</label>
              <input value={form.channel} onChange={e => set('channel', e.target.value)}
                className="mt-1 w-full border border-gray-200 rounded-xl px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="text-xs font-semibold text-gray-500">Customer ID</label>
              <input value={form.customer_id} onChange={e => set('customer_id', e.target.value)}
                className="mt-1 w-full border border-gray-200 rounded-xl px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="text-xs font-semibold text-gray-500">Session ID</label>
              <input value={form.session_id} onChange={e => set('session_id', e.target.value)}
                className="mt-1 w-full border border-gray-200 rounded-xl px-3 py-2 text-sm" />
            </div>
          </div>

          <div>
            <label className="text-xs font-semibold text-gray-500">Tags</label>
            <input value={form.tags} onChange={e => set('tags', e.target.value)} placeholder="billing, vip, outage"
              className="mt-1 w-full border border-gray-200 rounded-xl px-3 py-2 text-sm" />
          </div>

          <div>
            <label className="text-xs font-semibold text-gray-500">Internal Notes</label>
            <textarea value={form.internal_notes} onChange={e => set('internal_notes', e.target.value)} rows={3}
              className="mt-1 w-full border border-gray-200 rounded-xl px-3 py-2 text-sm" />
          </div>
        </div>

        <div className="p-5 border-t border-gray-100 flex justify-end gap-2">
          <button type="button" onClick={onClose} className="px-4 py-2 rounded-xl text-sm bg-gray-100 text-gray-600 hover:bg-gray-200">Cancel</button>
          <button disabled={busy} className="px-4 py-2 rounded-xl text-sm bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-60">
            {busy ? 'Creating...' : 'Create Case'}
          </button>
        </div>
      </form>
    </div>
  )
}

function CaseRow({ item, departments, onUpdated }) {
  const [expanded, setExpanded] = useState(false)
  const [draft, setDraft] = useState(() => ({
    status: item.status,
    priority: item.priority,
    department: item.department,
    owner: item.owner || '',
    internal_notes: item.internal_notes || '',
  }))
  const [busy, setBusy] = useState(false)
  const [activity, setActivity] = useState([])
  const [activityLoading, setActivityLoading] = useState(false)
  const [note, setNote] = useState('')
  const [noteBusy, setNoteBusy] = useState(false)
  const sla = timeState(item.sla_due_at, item.status)

  const fetchActivity = useCallback(async () => {
    setActivityLoading(true)
    try {
      const res = await fetch(`${api.base}/cases/${item.id}/activity`, {
        headers: { Authorization: `Bearer ${api.key}` },
      })
      const data = await res.json().catch(() => ({}))
      if (res.ok) setActivity(data.activity || [])
    } finally {
      setActivityLoading(false)
    }
  }, [item.id])

  useEffect(() => {
    if (expanded) fetchActivity()
  }, [expanded, fetchActivity])

  async function save() {
    setBusy(true)
    try {
      const res = await fetch(`${api.base}/cases/${item.id}`, {
        method: 'PATCH',
        headers: { Authorization: `Bearer ${api.key}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...draft, owner: draft.owner || null }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(data.detail || 'Failed to update case')
      onUpdated(data)
      await fetchActivity()
      setExpanded(false)
    } finally {
      setBusy(false)
    }
  }

  async function addNote() {
    if (!note.trim()) return
    setNoteBusy(true)
    try {
      const res = await fetch(`${api.base}/cases/${item.id}/notes`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${api.key}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ note }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(data.detail || 'Failed to add note')
      setDraft(d => ({ ...d, internal_notes: data.internal_notes || d.internal_notes }))
      setNote('')
      onUpdated(data)
      await fetchActivity()
    } finally {
      setNoteBusy(false)
    }
  }

  return (
    <div className="bg-white rounded-2xl shadow overflow-hidden">
      <button onClick={() => setExpanded(v => !v)} className="w-full text-left p-4 hover:bg-gray-50 transition">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2 mb-1">
              <span className="font-mono text-xs text-gray-400">{item.case_number}</span>
              <span className={`text-xs px-2 py-0.5 rounded-full border ${STATUS_STYLE[item.status] || STATUS_STYLE.pending}`}>
                {labelFor(MUTABLE_STATUSES, item.status)}
              </span>
              <span className={`text-xs px-2 py-0.5 rounded-full border ${PRIORITY_STYLE[item.priority] || PRIORITY_STYLE.normal}`}>
                {labelFor(MUTABLE_PRIORITIES, item.priority)}
              </span>
            </div>
            <div className="font-semibold text-gray-800 truncate">{item.title}</div>
            <div className="text-xs text-gray-400 mt-1">
              {item.department} · {item.owner || 'unassigned'} · {item.channel || 'unknown'} · {item.customer_id || 'no customer id'}
            </div>
          </div>
          <div className="text-right flex-shrink-0">
            <div className={`text-xs font-semibold ${sla.tone}`}>{sla.label}</div>
            <div className={`text-xs mt-0.5 font-semibold ${slaTone(item.sla_status)}`}>
              SLA {item.sla_status || 'ok'}
            </div>
            <div className="text-xs text-gray-400 mt-1">{formatTime(item.sla_due_at)}</div>
          </div>
        </div>
      </button>

      {expanded && (
        <div className="border-t border-gray-100 p-4 bg-gray-50">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <div className="lg:col-span-2 space-y-3">
              <div>
                <div className="text-xs text-gray-400 uppercase tracking-wide mb-1">Description</div>
                <div className="bg-white border border-gray-100 rounded-xl p-3 text-sm text-gray-700 whitespace-pre-wrap min-h-[80px]">
                  {item.description || 'No description'}
                </div>
              </div>
              <div>
                <label className="text-xs text-gray-400 uppercase tracking-wide mb-1 block">Internal Notes</label>
                <textarea value={draft.internal_notes} rows={4} onChange={e => setDraft(d => ({ ...d, internal_notes: e.target.value }))}
                  className="w-full bg-white border border-gray-200 rounded-xl p-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-100" />
              </div>
              {item.session_id && (
                <div className="text-xs text-gray-500">
                  Linked session: <span className="font-mono">{item.session_id}</span>
                </div>
              )}
              <div>
                <div className="text-xs text-gray-400 uppercase tracking-wide mb-1">Activity Timeline</div>
                <div className="bg-white border border-gray-100 rounded-xl p-3 max-h-64 overflow-y-auto">
                  {activityLoading ? (
                    <div className="text-xs text-gray-400 py-3 text-center">Loading activity...</div>
                  ) : activity.length === 0 ? (
                    <div className="text-xs text-gray-400 py-3 text-center">No activity yet</div>
                  ) : (
                    <div className="space-y-3">
                      {activity.map(event => (
                        <div key={event.id} className="flex gap-3">
                          <div className="w-2 h-2 rounded-full bg-blue-500 mt-1.5 flex-shrink-0" />
                          <div className="min-w-0">
                            <div className="text-sm text-gray-700 whitespace-pre-wrap">{activityText(event)}</div>
                            <div className="text-xs text-gray-400 mt-0.5">
                              {event.actor || 'system'} · {new Date(event.created_at).toLocaleString()}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>

            <div className="space-y-3">
              <div>
                <label className="text-xs font-semibold text-gray-500">Status</label>
                <select value={draft.status} onChange={e => setDraft(d => ({ ...d, status: e.target.value }))}
                  className="mt-1 w-full border border-gray-200 rounded-xl px-3 py-2 text-sm bg-white">
                  {MUTABLE_STATUSES.map(([v, label]) => <option key={v} value={v}>{label}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs font-semibold text-gray-500">Priority</label>
                <select value={draft.priority} onChange={e => setDraft(d => ({ ...d, priority: e.target.value }))}
                  className="mt-1 w-full border border-gray-200 rounded-xl px-3 py-2 text-sm bg-white">
                  {MUTABLE_PRIORITIES.map(([v, label]) => <option key={v} value={v}>{label}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs font-semibold text-gray-500">Department</label>
                <select value={draft.department} onChange={e => setDraft(d => ({ ...d, department: e.target.value }))}
                  className="mt-1 w-full border border-gray-200 rounded-xl px-3 py-2 text-sm bg-white">
                  {departments.map(d => <option key={d.code} value={d.code}>{d.name}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs font-semibold text-gray-500">Owner</label>
                <input value={draft.owner} onChange={e => setDraft(d => ({ ...d, owner: e.target.value }))}
                  className="mt-1 w-full border border-gray-200 rounded-xl px-3 py-2 text-sm bg-white" />
              </div>
              <button onClick={save} disabled={busy}
                className="w-full bg-blue-600 text-white rounded-xl py-2 text-sm font-semibold hover:bg-blue-700 disabled:opacity-60">
                {busy ? 'Saving...' : 'Save Case'}
              </button>
              <div className="bg-white border border-gray-100 rounded-xl p-3">
                <label className="text-xs font-semibold text-gray-500">Add Timeline Note</label>
                <textarea value={note} onChange={e => setNote(e.target.value)} rows={3}
                  className="mt-1 w-full border border-gray-200 rounded-xl px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-100" />
                <button onClick={addNote} disabled={noteBusy || !note.trim()}
                  className="mt-2 w-full bg-gray-900 text-white rounded-xl py-2 text-sm font-semibold hover:bg-gray-800 disabled:opacity-50">
                  {noteBusy ? 'Adding...' : 'Add Note'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default function Cases() {
  const [cases, setCases] = useState([])
  const [departments, setDepartments] = useState([])
  const [stats, setStats] = useState({})
  const [overdue, setOverdue] = useState(0)
  const [atRisk, setAtRisk] = useState(0)
  const [breached, setBreached] = useState(0)
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [createOpen, setCreateOpen] = useState(false)
  const [filters, setFilters] = useState({ status: 'all', priority: 'all', department: 'all', q: '' })

  const query = useMemo(() => {
    const params = new URLSearchParams()
    Object.entries(filters).forEach(([key, value]) => {
      if (value) params.set(key, value)
    })
    params.set('limit', '100')
    return params.toString()
  }, [filters])

  const fetchCases = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const res = await fetch(`${api.base}/cases?${query}`, {
        headers: { Authorization: `Bearer ${api.key}` },
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(data.detail || 'Failed to load cases')
      setCases(data.cases || [])
      setStats(data.stats || {})
      setOverdue(data.overdue || 0)
      setAtRisk(data.at_risk || 0)
      setBreached(data.breached || 0)
      setTotal(data.total || 0)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [query])

  useEffect(() => {
    async function loadDepartments() {
      try {
        const res = await fetch(`${api.base}/departments`, { headers: { Authorization: `Bearer ${api.key}` } })
        const data = await res.json()
        setDepartments(data.departments || [])
      } catch {}
    }
    loadDepartments()
  }, [])

  useEffect(() => { fetchCases() }, [fetchCases])

  function updateCase(updated) {
    setCases(items => items.map(item => item.id === updated.id ? updated : item))
    fetchCases()
  }

  const openCount = (stats.open || 0) + (stats.in_progress || 0) + (stats.waiting_customer || 0) + (stats.escalated || 0) + (stats.pending || 0)

  return (
    <div className="p-6 max-w-7xl">
      <div className="flex items-center justify-between gap-3 flex-wrap mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Cases</h1>
          <div className="text-xs text-gray-400 mt-1">Ticket workflow, ownership, departments and SLA tracking</div>
        </div>
        <div className="flex gap-2">
          <button onClick={fetchCases} className="px-3 py-2 rounded-xl bg-white border border-gray-200 text-sm text-gray-600 hover:bg-gray-50">
            Refresh
          </button>
          <button onClick={() => setCreateOpen(true)} className="px-4 py-2 rounded-xl bg-blue-600 text-white text-sm font-semibold hover:bg-blue-700">
            New Case
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-5">
        <Kpi label="Open Work" value={openCount} tone={openCount ? 'text-blue-600' : 'text-gray-500'} />
        <Kpi label="At Risk SLA" value={atRisk} tone={atRisk ? 'text-orange-600' : 'text-green-600'} />
        <Kpi label="Breached SLA" value={breached || overdue} tone={(breached || overdue) ? 'text-red-600' : 'text-green-600'} />
        <Kpi label="Escalated" value={stats.escalated || 0} tone={(stats.escalated || 0) ? 'text-red-600' : 'text-gray-500'} />
      </div>

      <div className="bg-white rounded-2xl shadow p-4 mb-5">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          <input value={filters.q} onChange={e => setFilters(f => ({ ...f, q: e.target.value }))}
            placeholder="Search case, session, customer..."
            className="border border-gray-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-100" />
          <select value={filters.status} onChange={e => setFilters(f => ({ ...f, status: e.target.value }))}
            className="border border-gray-200 rounded-xl px-3 py-2 text-sm bg-white">
            {STATUSES.map(([v, label]) => <option key={v} value={v}>{label}</option>)}
          </select>
          <select value={filters.priority} onChange={e => setFilters(f => ({ ...f, priority: e.target.value }))}
            className="border border-gray-200 rounded-xl px-3 py-2 text-sm bg-white">
            {PRIORITIES.map(([v, label]) => <option key={v} value={v}>{label}</option>)}
          </select>
          <select value={filters.department} onChange={e => setFilters(f => ({ ...f, department: e.target.value }))}
            className="border border-gray-200 rounded-xl px-3 py-2 text-sm bg-white">
            <option value="all">All Departments</option>
            {departments.map(d => <option key={d.code} value={d.code}>{d.name}</option>)}
          </select>
        </div>
      </div>

      {error && <div className="mb-4 bg-red-50 border border-red-100 text-red-700 rounded-xl px-4 py-3 text-sm">{error}</div>}

      <div className="mb-3 text-xs text-gray-400">
        {loading ? 'Loading cases...' : `${cases.length} shown${total > cases.length ? ` of ${total}` : ''}`}
      </div>

      {loading ? (
        <div className="text-center text-gray-400 py-16 text-sm">Loading cases...</div>
      ) : cases.length === 0 ? (
        <div className="bg-white rounded-2xl shadow p-12 text-center text-gray-400 text-sm">
          No cases found for this filter
        </div>
      ) : (
        <div className="space-y-3">
          {cases.map(item => (
            <CaseRow key={item.id} item={item} departments={departments} onUpdated={updateCase} />
          ))}
        </div>
      )}

      {createOpen && (
        <CreateCaseModal
          departments={departments}
          onClose={() => setCreateOpen(false)}
          onCreated={() => { setCreateOpen(false); fetchCases() }}
        />
      )}
    </div>
  )
}
