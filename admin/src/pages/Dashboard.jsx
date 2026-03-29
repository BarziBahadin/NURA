import React, { useState, useEffect } from 'react'
import { api } from '../App.jsx'

function StatusDot({ status }) {
  const color = status === 'ok' ? 'bg-green-400' : status === 'unknown' ? 'bg-yellow-400' : 'bg-red-400'
  return <span className={`inline-block w-2.5 h-2.5 rounded-full ${color}`} />
}

function StatCard({ label, value, sub }) {
  return (
    <div className="bg-white rounded-2xl shadow p-5">
      <div className="text-sm text-gray-500 mb-1">{label}</div>
      <div className="text-3xl font-bold text-gray-800">{value}</div>
      {sub && <div className="text-xs text-gray-400 mt-1">{sub}</div>}
    </div>
  )
}

export default function Dashboard() {
  const [health, setHealth] = useState(null)
  const [queue, setQueue] = useState(null)

  async function fetchData() {
    try {
      const headers = { Authorization: `Bearer ${api.key}` }
      const [h, q] = await Promise.all([
        fetch(`${api.base}/health`, { headers }).then(r => r.json()),
        fetch(`${api.base}/queue`, { headers }).then(r => r.json()),
      ])
      setHealth(h)
      setQueue(q)
    } catch (e) {
      console.error(e)
    }
  }

  useEffect(() => {
    fetchData()
    const t = setInterval(fetchData, 30000)
    return () => clearInterval(t)
  }, [])

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-gray-800 mb-6">لوحة التحكم</h1>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
        <StatCard label="الجلسات في الانتظار" value={queue?.pending ?? '—'} sub="بانتظار موظف بشري" />
        <StatCard label="حالة النظام" value={health?.status === 'ok' ? 'يعمل' : 'مشكلة'} sub={health ? 'آخر فحص: الآن' : 'جاري التحقق...'} />
        <StatCard label="الخدمات النشطة" value={health ? Object.values(health.services).filter(v => v === 'ok').length : '—'} sub={`من ${health ? Object.keys(health.services).length : '—'} خدمة`} />
      </div>

      {health && (
        <div className="bg-white rounded-2xl shadow p-5 mb-6">
          <h2 className="text-base font-semibold text-gray-700 mb-4">حالة الخدمات</h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {Object.entries(health.services).map(([name, status]) => (
              <div key={name} className="flex items-center gap-2 bg-gray-50 rounded-xl px-3 py-2">
                <StatusDot status={status} />
                <span className="text-sm text-gray-600">{name}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="bg-white rounded-2xl shadow p-5">
        <h2 className="text-base font-semibold text-gray-700 mb-2">معلومات النظام</h2>
        <ul className="text-sm text-gray-600 space-y-1">
          <li>• نموذج الذكاء الاصطناعي: <span className="font-mono text-blue-600">gpt-5.4-nano-2026-03-17</span></li>
          <li>• نموذج التضمين: <span className="font-mono text-blue-600">text-embedding-3-small</span></li>
          <li>• الشركة: <span className="font-mono text-blue-600">{window.COMPANY_NAME || 'configured in .env'}</span></li>
          <li>• القناة النشطة: ويب</li>
        </ul>
      </div>
    </div>
  )
}
