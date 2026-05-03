import React, { useState, useEffect } from 'react'
import { api } from '../App.jsx'

const ROLE_COLORS = {
  admin: 'bg-blue-100 text-blue-700',
  agent: 'bg-green-100 text-green-700',
  viewer: 'bg-gray-100 text-gray-600',
}

function timeAgo(iso) {
  if (!iso) return 'Never'
  const diff = Math.floor((Date.now() - new Date(iso)) / 1000)
  if (diff < 60) return 'just now'
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  return new Date(iso).toLocaleDateString('en')
}

function Modal({ title, children, onClose }) {
  return (
    <div className="fixed inset-0 bg-black/30 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-gray-800">{title}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl leading-none">×</button>
        </div>
        {children}
      </div>
    </div>
  )
}

function CreateModal({ onClose, onCreated }) {
  const [form, setForm] = useState({ username: '', password: '', confirm: '', role: 'agent', display_name: '' })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  async function submit(e) {
    e.preventDefault()
    if (form.password !== form.confirm) { setError('Passwords do not match'); return }
    setBusy(true); setError('')
    try {
      const res = await fetch(`${api.base}/users`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${api.key}` },
        body: JSON.stringify({ username: form.username, password: form.password, role: form.role, display_name: form.display_name }),
      })
      const data = await res.json()
      if (!res.ok) { setError(data.detail || 'Failed'); return }
      onCreated()
    } finally { setBusy(false) }
  }

  return (
    <Modal title="Add Team Member" onClose={onClose}>
      <form onSubmit={submit} className="space-y-3">
        <label className="block text-xs text-gray-500">
          Username
          <input value={form.username} onChange={e => set('username', e.target.value)} required
            className="mt-1 w-full border border-gray-200 rounded-xl px-3 py-2 text-sm" placeholder="agent1" />
        </label>
        <label className="block text-xs text-gray-500">
          Display Name
          <input value={form.display_name} onChange={e => set('display_name', e.target.value)}
            className="mt-1 w-full border border-gray-200 rounded-xl px-3 py-2 text-sm" placeholder="John Smith" />
        </label>
        <label className="block text-xs text-gray-500">
          Role
          <select value={form.role} onChange={e => set('role', e.target.value)}
            className="mt-1 w-full border border-gray-200 rounded-xl px-3 py-2 text-sm">
            <option value="agent">Agent</option>
            <option value="viewer">Viewer</option>
            <option value="admin">Admin</option>
          </select>
        </label>
        <label className="block text-xs text-gray-500">
          Password
          <input type="password" value={form.password} onChange={e => set('password', e.target.value)} required minLength={8}
            className="mt-1 w-full border border-gray-200 rounded-xl px-3 py-2 text-sm" />
        </label>
        <label className="block text-xs text-gray-500">
          Confirm Password
          <input type="password" value={form.confirm} onChange={e => set('confirm', e.target.value)} required
            className="mt-1 w-full border border-gray-200 rounded-xl px-3 py-2 text-sm" />
        </label>
        {error && <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-xl px-3 py-2">{error}</div>}
        <div className="flex justify-end gap-2 pt-1">
          <button type="button" onClick={onClose} className="px-4 py-2 text-sm rounded-xl bg-gray-100 text-gray-600 hover:bg-gray-200">Cancel</button>
          <button type="submit" disabled={busy} className="px-4 py-2 text-sm rounded-xl bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50">
            {busy ? 'Creating...' : 'Create'}
          </button>
        </div>
      </form>
    </Modal>
  )
}

function ResetPasswordModal({ username, onClose, onDone }) {
  const [pwd, setPwd] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(e) {
    e.preventDefault()
    if (pwd !== confirm) { setError('Passwords do not match'); return }
    setBusy(true); setError('')
    try {
      const res = await fetch(`${api.base}/users/${username}/password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${api.key}` },
        body: JSON.stringify({ new_password: pwd }),
      })
      if (!res.ok) { const d = await res.json(); setError(d.detail || 'Failed'); return }
      onDone()
    } finally { setBusy(false) }
  }

  return (
    <Modal title={`Reset Password — ${username}`} onClose={onClose}>
      <form onSubmit={submit} className="space-y-3">
        <label className="block text-xs text-gray-500">
          New Password
          <input type="password" value={pwd} onChange={e => setPwd(e.target.value)} required minLength={8}
            className="mt-1 w-full border border-gray-200 rounded-xl px-3 py-2 text-sm" />
        </label>
        <label className="block text-xs text-gray-500">
          Confirm Password
          <input type="password" value={confirm} onChange={e => setConfirm(e.target.value)} required
            className="mt-1 w-full border border-gray-200 rounded-xl px-3 py-2 text-sm" />
        </label>
        {error && <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-xl px-3 py-2">{error}</div>}
        <div className="flex justify-end gap-2 pt-1">
          <button type="button" onClick={onClose} className="px-4 py-2 text-sm rounded-xl bg-gray-100 text-gray-600 hover:bg-gray-200">Cancel</button>
          <button type="submit" disabled={busy} className="px-4 py-2 text-sm rounded-xl bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50">
            {busy ? 'Saving...' : 'Save'}
          </button>
        </div>
      </form>
    </Modal>
  )
}

export default function UserManagement() {
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [resetTarget, setResetTarget] = useState(null)

  async function fetchUsers() {
    setLoading(true)
    try {
      const res = await fetch(`${api.base}/users`, {
        headers: { Authorization: `Bearer ${api.key}` },
      })
      const data = await res.json()
      setUsers(data.users || [])
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchUsers() }, [])

  async function toggleActive(username, current) {
    await fetch(`${api.base}/users/${username}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${api.key}` },
      body: JSON.stringify({ is_active: !current }),
    })
    fetchUsers()
  }

  async function changeRole(username, role) {
    await fetch(`${api.base}/users/${username}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${api.key}` },
      body: JSON.stringify({ role }),
    })
    fetchUsers()
  }

  return (
    <div className="p-6 max-w-5xl">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-800">Team Members</h1>
        <button
          onClick={() => setShowCreate(true)}
          className="bg-blue-600 hover:bg-blue-700 text-white text-sm px-4 py-2 rounded-xl transition"
        >
          + Add Member
        </button>
      </div>

      {loading ? (
        <div className="text-center text-gray-400 py-20">Loading...</div>
      ) : (
        <div className="bg-white rounded-2xl shadow overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-100">
              <tr>
                <th className="text-left px-5 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Member</th>
                <th className="text-left px-5 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Role</th>
                <th className="text-left px-5 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Status</th>
                <th className="text-left px-5 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Last Login</th>
                <th className="px-5 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {users.map(u => (
                <tr key={u.username} className="hover:bg-gray-50 transition">
                  <td className="px-5 py-3">
                    <div className="font-medium text-gray-800">{u.display_name || u.username}</div>
                    <div className="text-xs text-gray-400">@{u.username}</div>
                  </td>
                  <td className="px-5 py-3">
                    <select
                      value={u.role}
                      onChange={e => changeRole(u.username, e.target.value)}
                      className={`text-xs font-medium px-2 py-1 rounded-full border-0 cursor-pointer ${ROLE_COLORS[u.role]}`}
                    >
                      <option value="admin">admin</option>
                      <option value="agent">agent</option>
                      <option value="viewer">viewer</option>
                    </select>
                  </td>
                  <td className="px-5 py-3">
                    <button
                      onClick={() => toggleActive(u.username, u.is_active)}
                      className={`text-xs font-medium px-2.5 py-1 rounded-full transition ${
                        u.is_active
                          ? 'bg-green-100 text-green-700 hover:bg-green-200'
                          : 'bg-red-100 text-red-600 hover:bg-red-200'
                      }`}
                    >
                      {u.is_active ? 'Active' : 'Inactive'}
                    </button>
                  </td>
                  <td className="px-5 py-3 text-xs text-gray-400">{timeAgo(u.last_login)}</td>
                  <td className="px-5 py-3 text-right">
                    <button
                      onClick={() => setResetTarget(u.username)}
                      className="text-xs text-blue-600 hover:underline"
                    >
                      Reset Password
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {users.length === 0 && (
            <div className="text-center text-gray-400 py-12">No team members yet</div>
          )}
        </div>
      )}

      {showCreate && (
        <CreateModal
          onClose={() => setShowCreate(false)}
          onCreated={() => { setShowCreate(false); fetchUsers() }}
        />
      )}
      {resetTarget && (
        <ResetPasswordModal
          username={resetTarget}
          onClose={() => setResetTarget(null)}
          onDone={() => setResetTarget(null)}
        />
      )}
    </div>
  )
}
