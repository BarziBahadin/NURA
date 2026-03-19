import React, { useState } from 'react'
import { api } from '../App.jsx'

const STATUS_LABELS = {
  ACTIVE: { label: 'نشط', color: 'bg-green-100 text-green-700' },
  PENDING_HANDOFF: { label: 'انتظار موظف', color: 'bg-yellow-100 text-yellow-700' },
  HUMAN_ACTIVE: { label: 'مع موظف', color: 'bg-blue-100 text-blue-700' },
  RESOLVED: { label: 'مغلق', color: 'bg-gray-100 text-gray-700' },
}

export default function SessionViewer() {
  const [sessionId, setSessionId] = useState('')
  const [session, setSession] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function fetchSession() {
    if (!sessionId.trim()) return
    setLoading(true)
    setError('')
    setSession(null)
    try {
      const res = await fetch(`${api.base}/session/${sessionId.trim()}`, {
        headers: { Authorization: `Bearer ${api.key}` },
      })
      if (!res.ok) throw new Error('الجلسة غير موجودة')
      const data = await res.json()
      setSession(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const statusInfo = session ? (STATUS_LABELS[session.status] || { label: session.status, color: 'bg-gray-100 text-gray-700' }) : null

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-gray-800 mb-6">عرض المحادثات</h1>

      <div className="flex gap-2 mb-6">
        <input
          type="text"
          value={sessionId}
          onChange={e => setSessionId(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && fetchSession()}
          placeholder="أدخل معرّف الجلسة..."
          className="flex-1 border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
        />
        <button
          onClick={fetchSession}
          disabled={loading}
          className="bg-blue-600 hover:bg-blue-700 text-white px-5 py-2.5 rounded-xl text-sm transition disabled:opacity-50"
        >
          {loading ? 'جاري...' : 'بحث'}
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-600 rounded-xl px-4 py-3 text-sm mb-4">
          {error}
        </div>
      )}

      {session && (
        <div className="bg-white rounded-2xl shadow overflow-hidden">
          <div className="p-4 border-b border-gray-100 flex flex-wrap gap-3 items-center">
            <span className="font-mono text-xs text-gray-400">{session.session_id}</span>
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${statusInfo.color}`}>
              {statusInfo.label}
            </span>
            <span className="text-xs text-gray-400">القناة: {session.channel}</span>
            <span className="text-xs text-gray-400">العميل: {session.customer_id}</span>
            <span className="text-xs text-gray-400 mr-auto">
              {new Date(session.created_at).toLocaleString('ar')}
            </span>
          </div>

          <div className="p-4 space-y-3 max-h-96 overflow-y-auto">
            {session.history?.length === 0 ? (
              <div className="text-center text-gray-400 py-6 text-sm">لا توجد رسائل</div>
            ) : (
              session.history.map((turn, i) => (
                <div key={i} className={`flex gap-2 ${turn.role === 'customer' ? 'flex-row-reverse' : ''}`}>
                  <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 ${
                    turn.role === 'agent' ? 'bg-blue-100 text-blue-600' : 'bg-gray-200 text-gray-600'
                  }`}>
                    {turn.role === 'agent' ? 'و' : 'ع'}
                  </div>
                  <div className={`max-w-sm ${turn.role === 'customer' ? 'items-end' : ''} flex flex-col`}>
                    <div className={`px-3 py-2 rounded-2xl text-sm ${
                      turn.role === 'agent'
                        ? 'bg-gray-100 text-gray-800 rounded-tl-sm'
                        : 'bg-blue-600 text-white rounded-tr-sm'
                    }`}>
                      {turn.message}
                    </div>
                    <div className="text-xs text-gray-400 mt-0.5">
                      {new Date(turn.timestamp).toLocaleTimeString('ar')}
                      {turn.confidence !== null && turn.confidence !== undefined && ` • دقة: ${Math.round(turn.confidence * 100)}%`}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  )
}
