import React, { useState, useEffect } from 'react'
import { api } from '../App.jsx'

export default function LiveQueue() {
  const [sessions, setSessions] = useState([])
  const [loading, setLoading] = useState(true)
  const [accepting, setAccepting] = useState({})

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

  useEffect(() => {
    fetchQueue()
    const t = setInterval(fetchQueue, 5000)
    return () => clearInterval(t)
  }, [])

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-800">قائمة الانتظار</h1>
        <span className="bg-red-100 text-red-700 text-sm font-semibold px-3 py-1 rounded-full">
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
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-mono text-xs text-gray-400">{s.session_id.split('-')[0]}...</span>
                  <span className="bg-yellow-100 text-yellow-700 text-xs px-2 py-0.5 rounded-full">
                    {s.channel}
                  </span>
                </div>
                <div className="text-sm text-gray-700 font-medium truncate">
                  العميل: {s.customer_id}
                </div>
                {s.history?.length > 0 && (
                  <div className="text-xs text-gray-400 truncate mt-0.5">
                    آخر رسالة: {s.history[s.history.length - 1]?.message?.slice(0, 80)}...
                  </div>
                )}
              </div>
              <button
                onClick={() => acceptSession(s.session_id)}
                disabled={accepting[s.session_id]}
                className="bg-blue-600 hover:bg-blue-700 text-white text-sm px-4 py-2 rounded-xl transition disabled:opacity-50 whitespace-nowrap"
              >
                {accepting[s.session_id] ? 'جاري...' : 'قبول'}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
