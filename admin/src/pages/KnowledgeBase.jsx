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
      setMessage({ type: 'success', text: data.message || 'File uploaded successfully' })
    } catch (e) {
      setMessage({ type: 'error', text: 'Upload failed: ' + e.message })
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
      setMessage({ type: 'success', text: data.message || 'Ingestion started in the background' })
    } catch (e) {
      setMessage({ type: 'error', text: 'Ingestion failed: ' + e.message })
    } finally {
      setIngesting(false)
    }
  }

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-gray-800 mb-6">Knowledge Base</h1>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
        <div className="bg-white rounded-2xl shadow p-5">
          <h2 className="text-base font-semibold text-gray-700 mb-3">Upload Handbook File</h2>
          <p className="text-sm text-gray-500 mb-4">
            Supported formats: PDF, DOCX, TXT, MD
          </p>
          <label className={`block w-full text-center py-3 px-4 rounded-xl border-2 border-dashed cursor-pointer transition ${
            uploading ? 'border-gray-200 text-gray-300' : 'border-blue-300 text-blue-600 hover:bg-blue-50'
          }`}>
            {uploading ? 'Uploading...' : 'Choose a file or drag and drop'}
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
          <h2 className="text-base font-semibold text-gray-700 mb-3">Re-index Knowledge</h2>
          <p className="text-sm text-gray-500 mb-4">
            Re-index all handbook files currently in ChromaDB.
          </p>
          <button
            onClick={triggerIngest}
            disabled={ingesting}
            className="w-full bg-green-600 hover:bg-green-700 text-white py-3 rounded-xl text-sm font-medium transition disabled:opacity-50"
          >
            {ingesting ? 'Indexing...' : 'Re-index All'}
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
        <h2 className="text-base font-semibold text-gray-700 mb-3">Instructions</h2>
        <ol className="text-sm text-gray-600 space-y-2 list-decimal list-inside">
          <li>Upload a handbook file (PDF, DOCX, or TXT)</li>
          <li>Indexing will start automatically in the background</li>
          <li>You can manually re-index if you update existing files</li>
          <li>Make sure the API container is running before indexing</li>
        </ol>
      </div>
    </div>
  )
}
