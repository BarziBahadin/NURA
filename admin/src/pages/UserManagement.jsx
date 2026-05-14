import React, { useEffect, useState } from 'react'
import { Users } from '@phosphor-icons/react'
import { apiGet, apiPatch, apiPost } from '../lib/apiFetch.js'
import {
  Badge,
  Button,
  Card,
  ConfirmDialog,
  EmptyState,
  Field,
  LoadingState,
  Modal,
  PageHeader,
  inputClass,
  useToast,
} from '../components/ui.jsx'

const ROLE_TONE = {
  admin: 'blue',
  agent: 'green',
  viewer: 'gray',
}

function timeAgo(iso) {
  if (!iso) return 'Never'
  const diff = Math.floor((Date.now() - new Date(iso)) / 1000)
  if (diff < 60) return 'just now'
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  return new Date(iso).toLocaleDateString('en')
}

function CreateModal({ onClose, onCreated }) {
  const toast = useToast()
  const [form, setForm] = useState({ username: '', password: '', confirm: '', role: 'agent', display_name: '' })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const set = (key, value) => setForm(current => ({ ...current, [key]: value }))

  async function submit(e) {
    e.preventDefault()
    if (form.password !== form.confirm) {
      setError('Passwords do not match')
      return
    }
    setBusy(true)
    setError('')
    try {
      await apiPost('/users', {
        username: form.username,
        password: form.password,
        role: form.role,
        display_name: form.display_name,
      })
      toast.success('Team member created')
      onCreated()
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal
      title="Add Team Member"
      onClose={onClose}
      footer={(
        <>
          <Button variant="secondary" onClick={onClose} disabled={busy}>Cancel</Button>
          <Button type="submit" form="create-user-form" disabled={busy}>{busy ? 'Creating...' : 'Create'}</Button>
        </>
      )}
    >
      <form id="create-user-form" onSubmit={submit} className="space-y-3">
        {error && <div className="rounded-lg border border-red-100 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>}
        <Field label="Username">
          <input value={form.username} onChange={e => set('username', e.target.value)} required className={inputClass} placeholder="agent1" />
        </Field>
        <Field label="Display Name">
          <input value={form.display_name} onChange={e => set('display_name', e.target.value)} className={inputClass} placeholder="John Smith" />
        </Field>
        <Field label="Role">
          <select value={form.role} onChange={e => set('role', e.target.value)} className={inputClass}>
            <option value="agent">Agent</option>
            <option value="viewer">Viewer</option>
            <option value="admin">Admin</option>
          </select>
        </Field>
        <Field label="Password">
          <input type="password" value={form.password} onChange={e => set('password', e.target.value)} required minLength={8} className={inputClass} />
        </Field>
        <Field label="Confirm Password">
          <input type="password" value={form.confirm} onChange={e => set('confirm', e.target.value)} required className={inputClass} />
        </Field>
      </form>
    </Modal>
  )
}

function ResetPasswordModal({ username, onClose, onDone }) {
  const toast = useToast()
  const [pwd, setPwd] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(e) {
    e.preventDefault()
    if (pwd !== confirm) {
      setError('Passwords do not match')
      return
    }
    setBusy(true)
    setError('')
    try {
      await apiPost(`/users/${username}/password`, { new_password: pwd })
      toast.success('Password reset')
      onDone()
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal
      title={`Reset Password - ${username}`}
      onClose={onClose}
      footer={(
        <>
          <Button variant="secondary" onClick={onClose} disabled={busy}>Cancel</Button>
          <Button type="submit" form="reset-password-form" disabled={busy}>{busy ? 'Saving...' : 'Save'}</Button>
        </>
      )}
    >
      <form id="reset-password-form" onSubmit={submit} className="space-y-3">
        {error && <div className="rounded-lg border border-red-100 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>}
        <Field label="New Password">
          <input type="password" value={pwd} onChange={e => setPwd(e.target.value)} required minLength={8} className={inputClass} />
        </Field>
        <Field label="Confirm Password">
          <input type="password" value={confirm} onChange={e => setConfirm(e.target.value)} required className={inputClass} />
        </Field>
      </form>
    </Modal>
  )
}

function UserCard({ user, onRoleChange, onToggleActive, onReset }) {
  return (
    <Card className="p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="font-semibold text-gray-900">{user.display_name || user.username}</div>
          <div className="text-xs text-gray-500">@{user.username}</div>
        </div>
        <Badge tone={user.is_active ? 'green' : 'red'}>{user.is_active ? 'Active' : 'Inactive'}</Badge>
      </div>
      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        <Field label="Role">
          <select value={user.role} onChange={e => onRoleChange(user, e.target.value)} className={inputClass}>
            <option value="admin">admin</option>
            <option value="agent">agent</option>
            <option value="viewer">viewer</option>
          </select>
        </Field>
        <div>
          <div className="text-xs font-semibold text-gray-500">Last Login</div>
          <div className="mt-2 text-sm text-gray-700">{timeAgo(user.last_login)}</div>
        </div>
        <div className="flex items-end gap-2 sm:justify-end">
          <Button variant="secondary" size="sm" onClick={() => onReset(user.username)}>Reset</Button>
          <Button variant={user.is_active ? 'danger' : 'primary'} size="sm" onClick={() => onToggleActive(user)}>
            {user.is_active ? 'Deactivate' : 'Activate'}
          </Button>
        </div>
      </div>
    </Card>
  )
}

export default function UserManagement() {
  const toast = useToast()
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showCreate, setShowCreate] = useState(false)
  const [resetTarget, setResetTarget] = useState(null)
  const [confirm, setConfirm] = useState(null)

  async function fetchUsers() {
    setLoading(true)
    setError('')
    try {
      const data = await apiGet('/users')
      setUsers(data.users || [])
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchUsers() }, [])

  function requestRoleChange(user, role) {
    if (role === user.role) return
    setConfirm({
      title: 'Change Role',
      message: `Change ${user.username} from ${user.role} to ${role}? Their current session will be invalidated.`,
      confirmLabel: 'Change Role',
      onConfirm: async () => {
        await apiPatch(`/users/${user.username}`, { role })
        toast.success('Role updated')
        setConfirm(null)
        fetchUsers()
      },
    })
  }

  function requestToggleActive(user) {
    setConfirm({
      title: user.is_active ? 'Deactivate User' : 'Activate User',
      message: `${user.is_active ? 'Deactivate' : 'Activate'} ${user.username}?`,
      confirmLabel: user.is_active ? 'Deactivate' : 'Activate',
      danger: user.is_active,
      onConfirm: async () => {
        await apiPatch(`/users/${user.username}`, { is_active: !user.is_active })
        toast.success(user.is_active ? 'User deactivated' : 'User activated')
        setConfirm(null)
        fetchUsers()
      },
    })
  }

  return (
    <div className="mx-auto w-full max-w-6xl p-4 md:p-6">
      <PageHeader
        title="Team Members"
        subtitle="Manage admin, agent, and viewer access."
        actions={<Button onClick={() => setShowCreate(true)}>Add Member</Button>}
      />

      {error && <div className="mb-4 rounded-lg border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}

      {loading ? (
        <LoadingState label="Loading team..." />
      ) : users.length === 0 ? (
        <EmptyState icon={<Users size={22} />} title="No team members yet" action={<Button onClick={() => setShowCreate(true)}>Add Member</Button>} />
      ) : (
        <>
          <div className="hidden overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm md:block">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">Member</th>
                  <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">Role</th>
                  <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">Status</th>
                  <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">Last Login</th>
                  <th className="px-5 py-3 text-right text-xs font-semibold uppercase tracking-wide text-gray-500">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {users.map(user => (
                  <tr key={user.username} className="hover:bg-gray-50">
                    <td className="px-5 py-3">
                      <div className="font-medium text-gray-900">{user.display_name || user.username}</div>
                      <div className="text-xs text-gray-500">@{user.username}</div>
                    </td>
                    <td className="px-5 py-3">
                      <select value={user.role} onChange={e => requestRoleChange(user, e.target.value)} className={`${inputClass} max-w-32 py-1`}>
                        <option value="admin">admin</option>
                        <option value="agent">agent</option>
                        <option value="viewer">viewer</option>
                      </select>
                    </td>
                    <td className="px-5 py-3">
                      <Badge tone={user.is_active ? 'green' : 'red'}>{user.is_active ? 'Active' : 'Inactive'}</Badge>
                    </td>
                    <td className="px-5 py-3 text-gray-500">{timeAgo(user.last_login)}</td>
                    <td className="px-5 py-3">
                      <div className="flex justify-end gap-2">
                        <Button variant="secondary" size="sm" onClick={() => setResetTarget(user.username)}>Reset</Button>
                        <Button variant={user.is_active ? 'danger' : 'primary'} size="sm" onClick={() => requestToggleActive(user)}>
                          {user.is_active ? 'Deactivate' : 'Activate'}
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="grid gap-3 md:hidden">
            {users.map(user => (
              <UserCard
                key={user.username}
                user={user}
                onRoleChange={requestRoleChange}
                onToggleActive={requestToggleActive}
                onReset={setResetTarget}
              />
            ))}
          </div>
        </>
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
          onDone={() => { setResetTarget(null); fetchUsers() }}
        />
      )}
      {confirm && (
        <ConfirmDialog
          title={confirm.title}
          message={confirm.message}
          confirmLabel={confirm.confirmLabel}
          danger={confirm.danger}
          onCancel={() => setConfirm(null)}
          onConfirm={async () => {
            try {
              await confirm.onConfirm()
            } catch (e) {
              toast.error(e.message)
              setConfirm(null)
            }
          }}
        />
      )}
    </div>
  )
}
