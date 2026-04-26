import React, { useState, useEffect } from 'react'
import { api } from '../App.jsx'

function waitingTime(iso) {
  const diff = Math.floor((Date.now() - new Date(iso)) / 1000)
  if (diff < 60) return `${diff} ث`
  if (diff < 3600) return `${Math.floor(diff / 60)} د`
  return `${Math.floor(diff / 3600)} س`
}

export default function LiveQueue() {
  const [sessions, setSessions] = useState([])
  const [loading, setLoading] = useState(true)
  const [accepting, setAccepting] = useState({})
  const [resolving, setResolving] = useState({})

  async function fetchQueue() {
    try {
      const res = await fetch(`${api.base}/queue`, {
        headers: { Authorization: `Bearer ${api.key}` },
      })
      const data = await res.json()
      setSessions(data.sessions || [])
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

  async function resolveSession(sessionId) {
    setResolving(r => ({ ...r, [sessionId]: true }))
    try {
      await fetch(`${api.base}/session/${sessionId}/resolve`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${api.key}` },
      })
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

  return (
    <div className="p-6 max-w-3xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-800">قائمة الانتظار</h1>
        <span className={`text-sm font-semibold px-3 py-1 rounded-full ${
          sessions.length > 0 ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'
        }`}>
          {sessions.length} في الانتظار
        </span>
      </div>

      {loading ? (
        <div className="text-center text-gray-400 py-12">جاري التحميل...</div>
      ) : sessions.length === 0 ? (
        <div className="bg-white rounded-2xl shadow p-10 text-center text-gray-400">
          <div className="text-4xl mb-3">✅</div>
          <div>لا توجد جلسات في الانتظار</div>
        </div>
      ) : (
        <div className="space-y-3">
          {sessions.map(s => (
            <div key={s.session_id} className="bg-white rounded-2xl shadow p-4 flex items-center gap-4">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1 flex-wrap">
                  <span className="font-mono text-xs text-gray-400">{s.session_id.split('-')[0]}...</span>
                  <span className="bg-yellow-100 text-yellow-700 text-xs px-2 py-0.5 rounded-full">
                    {s.channel}
                  </span>
                  <span className="bg-orange-100 text-orange-600 text-xs px-2 py-0.5 rounded-full font-medium">
                    ⏱ {waitingTime(s.updated_at)}
                  </span>
                </div>
                <div className="text-sm text-gray-700 font-medium truncate">
                  العميل: {s.customer_id}
                </div>
                {s.history?.length > 0 && (
                  <div className="text-xs text-gray-400 truncate mt-0.5">
                    آخر رسالة: {s.history[s.history.length - 1]?.message?.slice(0, 80)}
                  </div>
                )}
              </div>
              <div className="flex gap-2 flex-shrink-0">
                <button
                  onClick={() => resolveSession(s.session_id)}
                  disabled={resolving[s.session_id]}
                  className="bg-gray-100 hover:bg-gray-200 text-gray-600 text-sm px-3 py-2 rounded-xl transition disabled:opacity-50 whitespace-nowrap"
                >
                  {resolving[s.session_id] ? '...' : 'إغلاق'}
                </button>
                <button
                  onClick={() => acceptSession(s.session_id)}
                  disabled={accepting[s.session_id]}
                  className="bg-blue-600 hover:bg-blue-700 text-white text-sm px-4 py-2 rounded-xl transition disabled:opacity-50 whitespace-nowrap"
                >
                  {accepting[s.session_id] ? 'جاري...' : 'قبول'}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
