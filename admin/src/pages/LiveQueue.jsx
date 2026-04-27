import React, { useState, useEffect, useRef } from 'react'
import { api } from '../App.jsx'

function playBeep() {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)()
    const osc = ctx.createOscillator()
    const gain = ctx.createGain()
    osc.connect(gain)
    gain.connect(ctx.destination)
    osc.frequency.value = 880
    gain.gain.setValueAtTime(0.25, ctx.currentTime)
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.35)
    osc.start(ctx.currentTime)
    osc.stop(ctx.currentTime + 0.35)
  } catch (_) {}
}

const CANNED = [
  'سيتم معالجة طلبك خلال 24 ساعة',
  'هل تحتاج إلى مساعدة إضافية؟',
  'يُرجى تزويدنا برقم حسابك',
  'شكراً لتواصلك مع Rcell',
  'تمّ تسجيل شكواك بنجاح',
  'يُرجى الانتظار قليلاً',
]

const DEFAULT_OUTCOME = {
  status: 'solved',
  issue_category: '',
  root_cause: '',
  resolution_notes: '',
  resolved_by: 'Agent',
}

function ResolveModal({ sessionId, onCancel, onSubmit, busy }) {
  const [form, setForm] = useState(DEFAULT_OUTCOME)
  const set = (key, value) => setForm(f => ({ ...f, [key]: value }))
  return (
    <div className="fixed inset-0 bg-black/30 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-gray-800">Resolve Session</h2>
          <span className="font-mono text-xs text-gray-400">{sessionId.slice(0, 8)}…</span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <label className="text-xs text-gray-500">
            Status
            <select value={form.status} onChange={e => set('status', e.target.value)}
              className="mt-1 w-full border border-gray-200 rounded-xl px-3 py-2 text-sm">
              <option value="solved">Solved</option>
              <option value="unresolved">Unresolved</option>
              <option value="duplicate">Duplicate</option>
              <option value="spam">Spam</option>
            </select>
          </label>
          <label className="text-xs text-gray-500">
            Issue Category
            <input value={form.issue_category} onChange={e => set('issue_category', e.target.value)}
              className="mt-1 w-full border border-gray-200 rounded-xl px-3 py-2 text-sm" placeholder="internet, sim, billing..." />
          </label>
          <label className="text-xs text-gray-500 sm:col-span-2">
            Root Cause
            <input value={form.root_cause} onChange={e => set('root_cause', e.target.value)}
              className="mt-1 w-full border border-gray-200 rounded-xl px-3 py-2 text-sm" placeholder="missing info, customer request, technical issue..." />
          </label>
          <label className="text-xs text-gray-500 sm:col-span-2">
            Notes
            <textarea value={form.resolution_notes} onChange={e => set('resolution_notes', e.target.value)}
              rows={3} className="mt-1 w-full border border-gray-200 rounded-xl px-3 py-2 text-sm resize-none" />
          </label>
        </div>
        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onCancel} disabled={busy}
            className="px-3 py-2 rounded-xl text-sm bg-gray-100 text-gray-600 hover:bg-gray-200 disabled:opacity-50">
            Cancel
          </button>
          <button onClick={() => onSubmit(form)} disabled={busy}
            className="px-4 py-2 rounded-xl text-sm bg-red-600 text-white hover:bg-red-700 disabled:opacity-50">
            {busy ? 'Resolving...' : 'Resolve'}
          </button>
        </div>
      </div>
    </div>
  )
}

function waitingTime(iso) {
  const diff = Math.floor((Date.now() - new Date(iso)) / 1000)
  if (diff < 60) return `${diff}s`
  if (diff < 3600) return `${Math.floor(diff / 60)}m`
  return `${Math.floor(diff / 3600)}h`
}

function ChatHistory({ turns }) {
  const bottomRef = useRef(null)
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [turns])

  if (!turns || turns.length === 0)
    return <div className="text-center text-gray-400 text-xs py-3">No messages yet</div>

  return (
    <div className="space-y-2 max-h-64 overflow-y-auto p-3 bg-gray-50 rounded-xl">
      {turns.map((t, i) => (
        <div key={i} className={`flex gap-2 ${t.role === 'customer' ? '' : 'flex-row-reverse'}`}>
          <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 ${
            t.role === 'agent' ? 'bg-blue-100 text-blue-600' : 'bg-gray-200 text-gray-600'
          }`}>
            {t.role === 'agent' ? 'A' : 'C'}
          </div>
          <div className={`flex flex-col ${t.role === 'customer' ? '' : 'items-end'}`}>
            <div className={`px-3 py-1.5 rounded-2xl text-sm max-w-xs ${
              t.role === 'agent'
                ? 'bg-blue-600 text-white rounded-tr-sm'
                : 'bg-white border border-gray-200 text-gray-800 rounded-tl-sm'
            }`}>
              {t.message}
            </div>
            <div className="text-xs text-gray-400 mt-0.5">
              {new Date(t.timestamp).toLocaleTimeString('en', { hour: '2-digit', minute: '2-digit' })}
              {t.source === 'human' && <span className="ml-1 text-blue-400">• human</span>}
            </div>
          </div>
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  )
}

function ActiveChatCard({ s, onResolved }) {
  const [turns, setTurns] = useState(s.history || [])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [resolving, setResolving] = useState(false)
  const [showResolve, setShowResolve] = useState(false)
  const [customerTyping, setCustomerTyping] = useState(false)
  const inputRef = useRef(null)
  const esRef = useRef(null)
  const fallbackRef = useRef(null)
  const customerTypingTimerRef = useRef(null)
  const typingDebounceRef = useRef(null)

  async function fetchAllMessages() {
    try {
      const res = await fetch(`${api.base}/session/${s.session_id}/messages`, {
        headers: { Authorization: `Bearer ${api.key}` },
      })
      const data = await res.json()
      if (data.turns) setTurns(data.turns)
    } catch (e) {
      console.error(e)
    }
  }

  function appendTurn(t) {
    setTurns(prev => {
      const key = t.timestamp + t.message
      if (prev.some(x => x.timestamp + x.message === key)) return prev
      return [...prev, t]
    })
  }

  useEffect(() => {
    fetchAllMessages()

    const es = new EventSource(`${api.base}/session/${s.session_id}/stream`)
    esRef.current = es

    es.onmessage = (e) => {
      try {
        const event = JSON.parse(e.data)
        if (event.type === 'turn') appendTurn(event.turn)
        else if (event.type === 'typing' && event.sender === 'customer') {
          setCustomerTyping(true)
          clearTimeout(customerTypingTimerRef.current)
          customerTypingTimerRef.current = setTimeout(() => setCustomerTyping(false), 3000)
        }
      } catch (_) {}
    }

    es.onerror = () => {
      es.close()
      esRef.current = null
      fallbackRef.current = setInterval(fetchAllMessages, 8000)
    }

    return () => {
      es.close()
      clearInterval(fallbackRef.current)
      clearTimeout(customerTypingTimerRef.current)
      clearTimeout(typingDebounceRef.current)
    }
  }, [s.session_id])

  async function sendMessage() {
    const text = input.trim()
    if (!text || sending) return
    setSending(true)
    try {
      await fetch(`${api.base}/session/${s.session_id}/agent-message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${api.key}` },
        body: JSON.stringify({ message: text, agent_name: 'Agent' }),
      })
      setInput('')
      await fetchAllMessages()
    } catch (e) {
      console.error(e)
    } finally {
      setSending(false)
      inputRef.current?.focus()
    }
  }

  function onInputChange(e) {
    setInput(e.target.value)
    clearTimeout(typingDebounceRef.current)
    typingDebounceRef.current = setTimeout(() => {
      fetch(`${api.base}/session/${s.session_id}/typing?sender=agent`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${api.key}` },
      }).catch(() => {})
    }, 500)
  }

  function onKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  async function resolve(outcome) {
    setResolving(true)
    esRef.current?.close()
    clearInterval(fallbackRef.current)
    try {
      await fetch(`${api.base}/session/${s.session_id}/resolve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${api.key}` },
        body: JSON.stringify(outcome),
      })
      onResolved()
    } catch (e) {
      console.error(e)
      setResolving(false)
    }
  }

  return (
    <div className="bg-white rounded-2xl shadow overflow-hidden border-l-4 border-blue-500">
      {/* Header */}
      <div className="flex items-center gap-3 p-4 bg-blue-50 border-b border-blue-100">
        <span className="text-xs px-2 py-0.5 rounded-full font-medium bg-blue-100 text-blue-700 flex-shrink-0">
          With Agent
        </span>
        <div className="flex-1 min-w-0">
          <span className="font-mono text-xs text-gray-400">{s.session_id.split('-')[0]}…</span>
          <span className="ml-2 text-xs text-gray-600">{s.customer_id}</span>
        </div>
        <span className="bg-orange-100 text-orange-600 text-xs px-2 py-0.5 rounded-full font-medium flex-shrink-0">
          ⏱ {waitingTime(s.updated_at)}
        </span>
        <button
          onClick={() => setShowResolve(true)}
          disabled={resolving}
          className="bg-gray-100 hover:bg-red-50 hover:text-red-600 text-gray-600 text-sm px-3 py-1.5 rounded-lg transition disabled:opacity-50 flex-shrink-0"
        >
          {resolving ? '...' : 'Resolve'}
        </button>
      </div>
      {showResolve && (
        <ResolveModal
          sessionId={s.session_id}
          busy={resolving}
          onCancel={() => setShowResolve(false)}
          onSubmit={resolve}
        />
      )}

      {/* Chat history */}
      <div className="p-4">
        <ChatHistory turns={turns} />

        {/* Customer typing indicator */}
        {customerTyping && (
          <div className="text-xs text-gray-400 italic mt-1 mb-1 pr-1 text-right">
            العميل يكتب…
          </div>
        )}

        {/* Canned responses */}
        <div className="flex flex-wrap gap-1.5 mt-3">
          {CANNED.map((phrase, i) => (
            <button
              key={i}
              onClick={() => { setInput(phrase); inputRef.current?.focus() }}
              className="text-xs px-2.5 py-1 rounded-full border border-gray-200 bg-gray-50 text-gray-600 hover:bg-blue-50 hover:border-blue-300 hover:text-blue-700 transition whitespace-nowrap"
              style={{ direction: 'rtl' }}
            >
              {phrase}
            </button>
          ))}
        </div>

        {/* Reply box */}
        <div className="flex gap-2 mt-2">
          <textarea
            ref={inputRef}
            value={input}
            onChange={onInputChange}
            onKeyDown={onKeyDown}
            rows={2}
            placeholder="Type a reply… (Enter to send, Shift+Enter for newline)"
            className="flex-1 border border-gray-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 resize-none"
          />
          <button
            onClick={sendMessage}
            disabled={sending || !input.trim()}
            className="bg-blue-600 hover:bg-blue-700 text-white text-sm px-4 py-2 rounded-xl transition disabled:opacity-50 self-end whitespace-nowrap"
          >
            {sending ? '...' : 'Send'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default function LiveQueue() {
  const [sessions, setSessions] = useState([])
  const [loading, setLoading] = useState(true)
  const [accepting, setAccepting] = useState({})
  const [resolving, setResolving] = useState({})
  const [resolveTarget, setResolveTarget] = useState(null)
  const prevPendingRef = useRef(null)

  async function fetchQueue() {
    try {
      const res = await fetch(`${api.base}/queue`, {
        headers: { Authorization: `Bearer ${api.key}` },
      })
      const data = await res.json()
      const incoming = data.sessions || []
      const newPending = incoming.filter(s => s.status === 'PENDING_HANDOFF').length
      if (prevPendingRef.current !== null && newPending > prevPendingRef.current) {
        playBeep()
      }
      prevPendingRef.current = newPending
      setSessions(incoming)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  async function acceptSession(sessionId) {
    setAccepting(a => ({ ...a, [sessionId]: true }))
    try {
      await fetch(`${api.base}/handoff/${sessionId}/accept`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${api.key}` },
      })
      await fetchQueue()
    } catch (e) {
      console.error(e)
    } finally {
      setAccepting(a => ({ ...a, [sessionId]: false }))
    }
  }

  async function resolveSession(sessionId, outcome) {
    setResolving(r => ({ ...r, [sessionId]: true }))
    try {
      await fetch(`${api.base}/session/${sessionId}/resolve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${api.key}` },
        body: JSON.stringify(outcome),
      })
      setResolveTarget(null)
      await fetchQueue()
    } catch (e) {
      console.error(e)
    } finally {
      setResolving(r => ({ ...r, [sessionId]: false }))
    }
  }

  useEffect(() => {
    fetchQueue()
    const t = setInterval(fetchQueue, 5000)
    return () => clearInterval(t)
  }, [])

  const pending = sessions.filter(s => s.status === 'PENDING_HANDOFF')
  const active = sessions.filter(s => s.status === 'HUMAN_ACTIVE')

  return (
    <div className="p-6 max-w-3xl">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-800">Live Queue</h1>
        <div className="flex gap-2">
          {pending.length > 0 && (
            <span className="text-sm font-semibold px-3 py-1 rounded-full bg-red-100 text-red-700">
              {pending.length} waiting
            </span>
          )}
          {active.length > 0 && (
            <span className="text-sm font-semibold px-3 py-1 rounded-full bg-blue-100 text-blue-700">
              {active.length} active
            </span>
          )}
          {sessions.length === 0 && (
            <span className="text-sm font-semibold px-3 py-1 rounded-full bg-green-100 text-green-700">
              All clear
            </span>
          )}
        </div>
      </div>

      {loading ? (
        <div className="text-center text-gray-400 py-12">Loading...</div>
      ) : sessions.length === 0 ? (
        <div className="bg-white rounded-2xl shadow p-10 text-center text-gray-400">
          <div className="text-4xl mb-3">✅</div>
          <div>No sessions in queue</div>
        </div>
      ) : (
        <div className="space-y-3">
          {/* HUMAN_ACTIVE — full chat cards */}
          {active.map(s => (
            <ActiveChatCard key={s.session_id} s={s} onResolved={fetchQueue} />
          ))}

          {/* PENDING_HANDOFF — accept / resolve only */}
          {pending.map(s => (
            <div key={s.session_id} className="bg-white rounded-2xl shadow p-4 flex items-center gap-4">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1 flex-wrap">
                  <span className="font-mono text-xs text-gray-400">{s.session_id.split('-')[0]}…</span>
                  <span className="bg-yellow-100 text-yellow-700 text-xs px-2 py-0.5 rounded-full">
                    {s.channel}
                  </span>
                  <span className="bg-orange-100 text-orange-600 text-xs px-2 py-0.5 rounded-full font-medium">
                    ⏱ {waitingTime(s.updated_at)}
                  </span>
                </div>
                <div className="text-sm text-gray-700 font-medium truncate">
                  Customer: {s.customer_id}
                </div>
                {s.history?.length > 0 && (
                  <div className="text-xs text-gray-400 truncate mt-0.5">
                    Last message: {s.history[s.history.length - 1]?.message?.slice(0, 80)}
                  </div>
                )}
              </div>
              <div className="flex gap-2 flex-shrink-0">
                <button
                  onClick={() => setResolveTarget(s)}
                  disabled={resolving[s.session_id]}
                  className="bg-gray-100 hover:bg-gray-200 text-gray-600 text-sm px-3 py-2 rounded-xl transition disabled:opacity-50 whitespace-nowrap"
                >
                  {resolving[s.session_id] ? '...' : 'Resolve'}
                </button>
                <button
                  onClick={() => acceptSession(s.session_id)}
                  disabled={accepting[s.session_id]}
                  className="bg-blue-600 hover:bg-blue-700 text-white text-sm px-4 py-2 rounded-xl transition disabled:opacity-50 whitespace-nowrap"
                >
                  {accepting[s.session_id] ? '...' : 'Accept'}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
      {resolveTarget && (
        <ResolveModal
          sessionId={resolveTarget.session_id}
          busy={!!resolving[resolveTarget.session_id]}
          onCancel={() => setResolveTarget(null)}
          onSubmit={outcome => resolveSession(resolveTarget.session_id, outcome)}
        />
      )}
    </div>
  )
}
