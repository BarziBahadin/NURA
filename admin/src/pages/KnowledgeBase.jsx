import React, { useState, useRef } from 'react'
import { api } from '../App.jsx'

export default function KnowledgeBase() {
  const [uploading, setUploading] = useState(false)
  const [ingesting, setIngesting] = useState(false)
  const [message, setMessage] = useState(null)
  const fileRef = useRef()

  async function uploadFile(e) {
    const file = e.target.files[0]
    if (!file) return
    setUploading(true)
    setMessage(null)
    try {
      const form = new FormData()
      form.append('file', file)
      const res = await fetch(`${api.base}/knowledge/upload`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${api.key}` },
        body: form,
      })
      const data = await res.json()
      setMessage({ type: 'success', text: data.message || 'تم رفع الملف بنجاح' })
    } catch (e) {
      setMessage({ type: 'error', text: 'فشل رفع الملف: ' + e.message })
    } finally {
      setUploading(false)
      fileRef.current.value = ''
    }
  }

  async function triggerIngest() {
    setIngesting(true)
    setMessage(null)
    try {
      const res = await fetch(`${api.base}/knowledge/ingest`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${api.key}` },
      })
      const data = await res.json()
      setMessage({ type: 'success', text: data.message || 'بدأ الفهرسة في الخلفية' })
    } catch (e) {
      setMessage({ type: 'error', text: 'فشل تشغيل الفهرسة: ' + e.message })
    } finally {
      setIngesting(false)
    }
  }

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-gray-800 mb-6">قاعدة المعرفة</h1>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
        <div className="bg-white rounded-2xl shadow p-5">
          <h2 className="text-base font-semibold text-gray-700 mb-3">رفع ملف الدليل</h2>
          <p className="text-sm text-gray-500 mb-4">
            الصيغ المدعومة: PDF, DOCX, TXT, MD
          </p>
          <label className={`block w-full text-center py-3 px-4 rounded-xl border-2 border-dashed cursor-pointer transition ${
            uploading ? 'border-gray-200 text-gray-300' : 'border-blue-300 text-blue-600 hover:bg-blue-50'
          }`}>
            {uploading ? 'جاري الرفع...' : 'اختر ملفاً أو اسحب وأفلت'}
            <input
              ref={fileRef}
              type="file"
              accept=".pdf,.docx,.txt,.md"
              onChange={uploadFile}
              disabled={uploading}
              className="hidden"
            />
          </label>
        </div>

        <div className="bg-white rounded-2xl shadow p-5">
          <h2 className="text-base font-semibold text-gray-700 mb-3">إعادة الفهرسة</h2>
          <p className="text-sm text-gray-500 mb-4">
            أعد فهرسة جميع ملفات الدليل الموجودة في ChromaDB.
          </p>
          <button
            onClick={triggerIngest}
            disabled={ingesting}
            className="w-full bg-green-600 hover:bg-green-700 text-white py-3 rounded-xl text-sm font-medium transition disabled:opacity-50"
          >
            {ingesting ? 'جاري الفهرسة...' : 'إعادة فهرسة الكل'}
          </button>
        </div>
      </div>

      {message && (
        <div className={`rounded-xl px-4 py-3 text-sm ${
          message.type === 'success'
            ? 'bg-green-50 border border-green-200 text-green-700'
            : 'bg-red-50 border border-red-200 text-red-600'
        }`}>
          {message.text}
        </div>
      )}

      <div className="bg-white rounded-2xl shadow p-5 mt-4">
        <h2 className="text-base font-semibold text-gray-700 mb-3">تعليمات</h2>
        <ol className="text-sm text-gray-600 space-y-2 list-decimal list-inside">
          <li>ارفع ملف دليل الشركة (PDF أو DOCX أو TXT)</li>
          <li>ستبدأ الفهرسة تلقائياً في الخلفية</li>
          <li>يمكنك إعادة الفهرسة يدوياً إذا قمت بتحديث الملفات</li>
          <li>تأكد من أن SSH tunnel نشط حتى تعمل الفهرسة بشكل صحيح</li>
        </ol>
      </div>
    </div>
  )
}
