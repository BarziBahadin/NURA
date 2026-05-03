import React, { useEffect, useState, useCallback } from 'react'
import { api } from '../App.jsx'

const STATUSES = [
  ['pending', 'Pending'],
  ['drafted', 'Drafted'],
  ['approved', 'Approved'],
  ['resolved', 'Resolved'],
  ['rejected', 'Rejected'],
  ['all', 'All'],
]

const STATUS_STYLES = {
  pending: 'bg-yellow-100 text-yellow-700',
  drafted: 'bg-blue-100 text-blue-700',
  approved: 'bg-green-100 text-green-700',
  resolved: 'bg-gray-100 text-gray-600',
  rejected: 'bg-red-100 text-red-600',
}

function StatusBadge({ status }) {
  return (
    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${STATUS_STYLES[status] || 'bg-gray-100 text-gray-500'}`}>
      {status}
    </span>
  )
}

function GapCard({ review, onChanged }) {
  const [answer, setAnswer] = useState(review.proposed_answer || review.approved_answer || '')
  const [notes, setNotes] = useState(review.notes || '')
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    setAnswer(review.proposed_answer || review.approved_answer || '')
    setNotes(review.notes || '')
  }, [review])

  async function send(path, method = 'POST', body = {}) {
    setBusy(path)
    setError('')
    try {
      const res = await fetch(`${api.base}${path}`, {
        method,
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${api.key}`,
        },
        body: JSON.stringify(body),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Request failed')
      onChanged(data.review)
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy('')
    }
  }

  function saveDraft() {
    send(`/knowledge-gaps/${review.id}`, 'PATCH', {
      proposed_answer: answer,
      notes,
      status: 'drafted',
    })
  }

  function approve() {
    send(`/knowledge-gaps/${review.id}/approve`, 'POST', { answer, notes })
  }

  function resolve() {
    send(`/knowledge-gaps/${review.id}/resolve`, 'POST', { notes })
  }

  function reject() {
    send(`/knowledge-gaps/${review.id}/reject`, 'POST', { notes })
  }

  const disabled = Boolean(busy)

  return (
    <div className="bg-white rounded-2xl shadow p-5">
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2 mb-2">
            <StatusBadge status={review.status} />
            {review.intent && (
              <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">{review.intent}</span>
            )}
            {review.channel && (
              <span className="text-xs text-gray-400">{review.channel}</span>
            )}
          </div>
          <div className="text-base font-semibold text-gray-800 leading-snug">{review.customer_message}</div>
        </div>
        <button
          onClick={() => window.location.assign('/sessions')}
          className="text-xs bg-gray-100 hover:bg-gray-200 text-gray-600 px-3 py-1.5 rounded-lg transition flex-shrink-0"
        >
          View Sessions
        </button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs text-gray-500 mb-4">
        <div>
          <div className="text-gray-400">Reason</div>
          <div className="text-gray-700 truncate">{review.gap_reason || '—'}</div>
        </div>
        <div>
          <div className="text-gray-400">Sub-intent</div>
          <div className="text-gray-700 truncate">{review.sub_intent || '—'}</div>
        </div>
        <div>
          <div className="text-gray-400">Created</div>
          <div className="text-gray-700">{review.created_at ? new Date(review.created_at).toLocaleString() : '—'}</div>
        </div>
      </div>

      <label className="block text-xs text-gray-500 mb-3">
        Approved answer candidate
        <textarea
          value={answer}
          onChange={e => setAnswer(e.target.value)}
          rows={4}
          className="mt-1 w-full border border-gray-200 rounded-xl px-3 py-2 text-sm text-gray-800 resize-y focus:outline-none focus:ring-2 focus:ring-blue-400"
          placeholder="Write the answer future customers should receive for this kind of question..."
        />
      </label>

      <label className="block text-xs text-gray-500 mb-4">
        Internal notes
        <input
          value={notes}
          onChange={e => setNotes(e.target.value)}
          className="mt-1 w-full border border-gray-200 rounded-xl px-3 py-2 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-400"
          placeholder="Why this was approved, rejected, or resolved"
        />
      </label>

      {error && <div className="text-xs text-red-600 bg-red-50 border border-red-100 rounded-lg px-3 py-2 mb-3">{error}</div>}

      <div className="flex flex-wrap gap-2">
        <button
          onClick={saveDraft}
          disabled={disabled || !answer.trim()}
          className="bg-blue-600 hover:bg-blue-700 text-white text-sm px-4 py-2 rounded-xl transition disabled:opacity-50"
        >
          {busy === `/knowledge-gaps/${review.id}` ? 'Saving...' : 'Save Draft'}
        </button>
        <button
          onClick={approve}
          disabled={disabled || !answer.trim()}
          className="bg-green-600 hover:bg-green-700 text-white text-sm px-4 py-2 rounded-xl transition disabled:opacity-50"
        >
          Approve
        </button>
        <button
          onClick={resolve}
          disabled={disabled}
          className="bg-gray-800 hover:bg-gray-900 text-white text-sm px-4 py-2 rounded-xl transition disabled:opacity-50"
        >
          Resolve
        </button>
        <button
          onClick={reject}
          disabled={disabled}
          className="bg-red-50 hover:bg-red-100 text-red-600 text-sm px-4 py-2 rounded-xl transition disabled:opacity-50"
        >
          Reject
        </button>
      </div>
    </div>
  )
}

export default function KnowledgeGapQueue() {
  const [reviews, setReviews] = useState([])
  const [counts, setCounts] = useState({})
  const [status, setStatus] = useState('pending')
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const fetchReviews = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const params = new URLSearchParams({ status, limit: 100 })
      if (query.trim()) params.set('q', query.trim())
      const res = await fetch(`${api.base}/knowledge-gaps?${params}`, {
        headers: { Authorization: `Bearer ${api.key}` },
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Failed to load knowledge gaps')
      setReviews(data.reviews || [])
      setCounts(data.counts || {})
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [status, query])

  useEffect(() => { fetchReviews() }, [fetchReviews])

  function replaceReview(next) {
    setReviews(rows => rows.map(r => r.id === next.id ? next : r))
    fetchReviews()
  }

  return (
    <div className="p-6 max-w-6xl">
      <div className="flex items-center justify-between gap-3 mb-5 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Knowledge Gap Queue</h1>
          <div className="text-sm text-gray-400 mt-1">Turn failed customer questions into reviewed answers the AI can reuse.</div>
        </div>
        <button
          onClick={fetchReviews}
          className="bg-white border border-gray-200 hover:bg-gray-50 text-gray-600 text-sm px-4 py-2 rounded-xl transition"
        >
          Refresh
        </button>
      </div>

      <div className="bg-white rounded-2xl shadow p-4 mb-5">
        <div className="flex flex-wrap items-center gap-2">
          {STATUSES.map(([key, label]) => (
            <button
              key={key}
              onClick={() => setStatus(key)}
              className={`text-sm px-3 py-1.5 rounded-xl transition ${
                status === key ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {label}
              {key !== 'all' && <span className="ml-1 opacity-70">{counts[key] || 0}</span>}
            </button>
          ))}
          <div className="flex-1 min-w-[220px]" />
          <input
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') fetchReviews() }}
            placeholder="Search message, intent, reason"
            className="border border-gray-200 rounded-xl px-3 py-2 text-sm min-w-[240px] focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
        </div>
      </div>

      {error && <div className="text-sm text-red-600 bg-red-50 border border-red-100 rounded-xl px-4 py-3 mb-4">{error}</div>}

      {loading ? (
        <div className="text-center text-gray-400 py-16 text-sm">Loading knowledge gaps...</div>
      ) : reviews.length === 0 ? (
        <div className="bg-white rounded-2xl shadow p-10 text-center text-gray-400">
          No knowledge gaps in this view
        </div>
      ) : (
        <div className="space-y-4">
          {reviews.map(review => (
            <GapCard key={review.id} review={review} onChanged={replaceReview} />
          ))}
        </div>
      )}
    </div>
  )
}
