import React, { useState, useEffect } from 'react'
import { api } from '../App.jsx'

const EMPTY_FORM = { title: '', body: '', category: '', language: 'ar', sort_order: 0 }

function ReplyModal({ initial, onSave, onClose, saving }) {
  const [form, setForm] = useState(initial || EMPTY_FORM)
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))
  const isNew = !initial

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg">
        <div className="flex items-center justify-between px-5 pt-5 pb-3 border-b border-gray-100">
          <h2 className="text-base font-bold text-gray-800">
            {isNew ? 'New Canned Reply' : 'Edit Canned Reply'}
          </h2>
          <button onClick={onClose} className="w-7 h-7 rounded-full hover:bg-gray-100 text-gray-400 hover:text-gray-700 transition text-lg leading-none">✕</button>
        </div>
        <div className="p-5 space-y-3">
          <label className="block text-xs font-medium text-gray-500">
            Title / Label
            <input
              value={form.title}
              onChange={e => set('title', e.target.value)}
              placeholder="e.g. Please hold"
              className="mt-1 w-full border border-gray-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
            />
          </label>
          <label className="block text-xs font-medium text-gray-500">
            Message Body
            <textarea
              value={form.body}
              onChange={e => set('body', e.target.value)}
              rows={4}
              placeholder="The pre-written message text…"
              className="mt-1 w-full border border-gray-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 resize-none"
              style={{ direction: 'auto' }}
            />
          </label>
          <div className="grid grid-cols-2 gap-3">
            <label className="block text-xs font-medium text-gray-500">
              Category
              <input
                value={form.category}
                onChange={e => set('category', e.target.value)}
                placeholder="general, billing, sim…"
                className="mt-1 w-full border border-gray-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
              />
            </label>
            <label className="block text-xs font-medium text-gray-500">
              Language
              <select
                value={form.language}
                onChange={e => set('language', e.target.value)}
                className="mt-1 w-full border border-gray-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
              >
                <option value="ar">Arabic</option>
                <option value="en">English</option>
                <option value="both">Both</option>
              </select>
            </label>
          </div>
          <label className="block text-xs font-medium text-gray-500">
            Sort Order
            <input
              type="number"
              value={form.sort_order}
              onChange={e => set('sort_order', parseInt(e.target.value) || 0)}
              className="mt-1 w-28 border border-gray-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
            />
          </label>
        </div>
        <div className="flex justify-end gap-2 px-5 pb-5">
          <button onClick={onClose} className="px-4 py-2 rounded-xl text-sm bg-white border border-gray-200 text-gray-600 hover:bg-gray-50">Cancel</button>
          <button
            onClick={() => onSave(form)}
            disabled={saving || !form.title.trim() || !form.body.trim()}
            className="px-4 py-2 rounded-xl text-sm bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {saving ? 'Saving…' : isNew ? 'Create' : 'Save Changes'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default function CannedReplies() {
  const [replies, setReplies] = useState([])
  const [loading, setLoading] = useState(true)
  const [editing, setEditing] = useState(null)
  const [creating, setCreating] = useState(false)
  const [saving, setSaving] = useState(false)
  const [deleting, setDeleting] = useState(null)
  const [filterCat, setFilterCat] = useState('')
  const [search, setSearch] = useState('')

  async function load() {
    try {
      const res = await fetch(`${api.base}/canned-replies`, {
        headers: { Authorization: `Bearer ${api.key}` },
      })
      const data = await res.json()
      setReplies(data.replies || [])
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  async function handleSave(form) {
    setSaving(true)
    try {
      const url = editing
        ? `${api.base}/canned-replies/${editing.id}`
        : `${api.base}/canned-replies`
      const method = editing ? 'PUT' : 'POST'
      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${api.key}` },
        body: JSON.stringify(form),
      })
      if (!res.ok) throw new Error(await res.text())
      setEditing(null)
      setCreating(false)
      await load()
    } catch (e) {
      alert('Failed to save: ' + e.message)
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(id) {
    if (!confirm('Delete this canned reply?')) return
    setDeleting(id)
    try {
      await fetch(`${api.base}/canned-replies/${id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${api.key}` },
      })
      await load()
    } catch (e) {
      console.error(e)
    } finally {
      setDeleting(null)
    }
  }

  const categories = [...new Set(replies.map(r => r.category).filter(Boolean))].sort()

  const visible = replies.filter(r => {
    const catMatch = !filterCat || r.category === filterCat
    const q = search.toLowerCase()
    const textMatch = !q || r.title.toLowerCase().includes(q) || r.body.toLowerCase().includes(q)
    return catMatch && textMatch
  })

  return (
    <div className="p-6 max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-gray-800">Canned Replies</h1>
          <p className="text-sm text-gray-500 mt-0.5">Pre-written messages agents can send with one click</p>
        </div>
        <button
          onClick={() => setCreating(true)}
          className="bg-blue-600 hover:bg-blue-700 text-white text-sm px-4 py-2 rounded-xl transition"
        >
          + New Reply
        </button>
      </div>

      {/* Filters */}
      <div className="flex gap-3 mb-4 flex-wrap">
        <input
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Search replies…"
          className="border border-gray-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 w-56"
        />
        <select
          value={filterCat}
          onChange={e => setFilterCat(e.target.value)}
          className="border border-gray-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
        >
          <option value="">All categories</option>
          {categories.map(c => <option key={c} value={c}>{c}</option>)}
        </select>
        <span className="text-xs text-gray-400 self-center">{visible.length} of {replies.length}</span>
      </div>

      {/* Table */}
      {loading ? (
        <div className="text-center text-gray-400 py-12">Loading…</div>
      ) : visible.length === 0 ? (
        <div className="text-center text-gray-400 py-12 bg-gray-50 rounded-2xl border border-dashed border-gray-200">
          {replies.length === 0
            ? 'No canned replies yet. Click "+ New Reply" to add the first one.'
            : 'No replies match your filter.'}
        </div>
      ) : (
        <div className="space-y-2">
          {visible.map(r => (
            <div key={r.id} className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4 flex gap-4 items-start">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1 flex-wrap">
                  <span className="font-semibold text-sm text-gray-800">{r.title}</span>
                  {r.category && (
                    <span className="text-xs px-2 py-0.5 rounded-full bg-blue-50 text-blue-600 border border-blue-100">{r.category}</span>
                  )}
                  <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-500">{r.language}</span>
                  {r.sort_order !== 0 && (
                    <span className="text-xs text-gray-400">#{r.sort_order}</span>
                  )}
                </div>
                <p
                  className="text-sm text-gray-600 whitespace-pre-wrap line-clamp-3"
                  style={{ direction: 'auto' }}
                >
                  {r.body}
                </p>
                {r.updated_by && (
                  <p className="text-xs text-gray-400 mt-1">Last edited by {r.updated_by}</p>
                )}
              </div>
              <div className="flex gap-2 flex-shrink-0">
                <button
                  onClick={() => setEditing(r)}
                  className="text-xs px-3 py-1.5 rounded-lg border border-gray-200 text-gray-600 hover:bg-blue-50 hover:border-blue-300 hover:text-blue-700 transition"
                >
                  Edit
                </button>
                <button
                  onClick={() => handleDelete(r.id)}
                  disabled={deleting === r.id}
                  className="text-xs px-3 py-1.5 rounded-lg border border-red-100 text-red-500 hover:bg-red-50 transition disabled:opacity-50"
                >
                  {deleting === r.id ? '…' : 'Delete'}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modals */}
      {creating && (
        <ReplyModal onSave={handleSave} onClose={() => setCreating(false)} saving={saving} />
      )}
      {editing && (
        <ReplyModal initial={editing} onSave={handleSave} onClose={() => setEditing(null)} saving={saving} />
      )}
    </div>
  )
}
