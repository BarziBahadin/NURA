import React, { createContext, forwardRef, useContext, useEffect, useRef, useState } from 'react'
import { CheckCircle, Info, Warning, X, XCircle } from '@phosphor-icons/react'

const toneClasses = {
  primary: 'bg-gray-900 text-white hover:bg-gray-800 focus:ring-gray-300',
  secondary: 'bg-white text-gray-700 border border-gray-200 hover:bg-gray-50 focus:ring-gray-200',
  danger: 'bg-red-600 text-white hover:bg-red-700 focus:ring-red-200',
  ghost: 'bg-transparent text-gray-600 hover:bg-gray-100 focus:ring-gray-200',
}

export function Button({ children, variant = 'primary', size = 'md', className = '', type = 'button', ...props }) {
  const sizes = {
    sm: 'h-8 px-3 text-xs',
    md: 'h-10 px-4 text-sm',
    lg: 'h-11 px-5 text-sm',
  }
  return (
    <button
      type={type}
      className={`inline-flex items-center justify-center gap-2 rounded-lg font-semibold transition focus:outline-none focus:ring-2 disabled:opacity-50 disabled:cursor-not-allowed ${toneClasses[variant] || toneClasses.primary} ${sizes[size] || sizes.md} ${className}`}
      {...props}
    >
      {children}
    </button>
  )
}

export const IconButton = forwardRef(function IconButton({ label, children, className = '', ...props }, ref) {
  return (
    <button
      ref={ref}
      type="button"
      aria-label={label}
      title={label}
      className={`inline-flex h-9 w-9 items-center justify-center rounded-lg border border-gray-200 bg-white text-gray-500 transition hover:bg-gray-50 hover:text-gray-800 focus:outline-none focus:ring-2 focus:ring-gray-200 disabled:opacity-50 ${className}`}
      {...props}
    >
      {children}
    </button>
  )
})

export function Badge({ children, tone = 'gray', className = '' }) {
  const tones = {
    gray: 'bg-gray-100 text-gray-700 border-gray-200',
    blue: 'bg-blue-50 text-blue-700 border-blue-100',
    green: 'bg-green-50 text-green-700 border-green-100',
    amber: 'bg-amber-50 text-amber-700 border-amber-100',
    red: 'bg-red-50 text-red-700 border-red-100',
    indigo: 'bg-indigo-50 text-indigo-700 border-indigo-100',
  }
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-semibold ${tones[tone] || tones.gray} ${className}`}>
      {children}
    </span>
  )
}

export function Card({ children, className = '' }) {
  return <div className={`rounded-lg border border-gray-200 bg-white shadow-sm ${className}`}>{children}</div>
}

export function PageHeader({ title, subtitle, actions }) {
  return (
    <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
      <div className="min-w-0">
        <h1 className="text-xl font-semibold tracking-tight text-gray-900">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-gray-500">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  )
}

export function LoadingState({ label = 'Loading...' }) {
  return (
    <div className="flex min-h-40 items-center justify-center rounded-lg border border-dashed border-gray-200 bg-white text-sm text-gray-400">
      {label}
    </div>
  )
}

export function EmptyState({ icon, title = 'Nothing here', description, action }) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white px-6 py-12 text-center">
      {icon && <div className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-lg bg-gray-50 text-gray-400">{icon}</div>}
      <div className="text-sm font-semibold text-gray-700">{title}</div>
      {description && <div className="mx-auto mt-1 max-w-md text-sm text-gray-400">{description}</div>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}

export function Field({ label, children, className = '' }) {
  return (
    <label className={`block text-xs font-semibold text-gray-500 ${className}`}>
      {label}
      <div className="mt-1">{children}</div>
    </label>
  )
}

export const inputClass = 'w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-800 outline-none transition focus:border-gray-400 focus:ring-2 focus:ring-gray-100 disabled:opacity-60'

export function Modal({ title, subtitle, children, footer, onClose, maxWidth = 'max-w-lg' }) {
  const panelRef = useRef(null)
  const closeRef = useRef(null)

  useEffect(() => {
    const previous = document.activeElement
    closeRef.current?.focus()
    function onKeyDown(e) {
      if (e.key === 'Escape') onClose?.()
      if (e.key !== 'Tab' || !panelRef.current) return
      const items = panelRef.current.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])')
      const focusable = Array.from(items).filter(el => !el.disabled)
      if (!focusable.length) return
      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault()
        last.focus()
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault()
        first.focus()
      }
    }
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('keydown', onKeyDown)
      previous?.focus?.()
    }
  }, [onClose])

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-950/40 p-4">
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
        className={`max-h-[90vh] w-full ${maxWidth} overflow-hidden rounded-lg bg-white shadow-xl`}
      >
        <div className="flex items-start justify-between gap-3 border-b border-gray-100 px-5 py-4">
          <div className="min-w-0">
            <h2 id="modal-title" className="text-base font-semibold text-gray-900">{title}</h2>
            {subtitle && <p className="mt-1 text-sm text-gray-500">{subtitle}</p>}
          </div>
          <IconButton ref={closeRef} label="Close" onClick={onClose} className="border-transparent">
            <X size={18} />
          </IconButton>
        </div>
        <div className="max-h-[calc(90vh-130px)] overflow-y-auto px-5 py-4">{children}</div>
        {footer && <div className="flex justify-end gap-2 border-t border-gray-100 bg-gray-50 px-5 py-4">{footer}</div>}
      </div>
    </div>
  )
}

const ToastContext = createContext(null)

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])
  function push(toast) {
    const id = `${Date.now()}-${Math.random()}`
    setToasts(items => [...items, { id, tone: 'info', ...toast }])
    setTimeout(() => setToasts(items => items.filter(item => item.id !== id)), toast.duration || 4000)
  }
  const value = {
    success: message => push({ tone: 'success', message }),
    error: message => push({ tone: 'error', message }),
    info: message => push({ tone: 'info', message }),
  }
  const icons = {
    success: <CheckCircle size={18} weight="fill" />,
    error: <XCircle size={18} weight="fill" />,
    warning: <Warning size={18} weight="fill" />,
    info: <Info size={18} weight="fill" />,
  }
  const tones = {
    success: 'border-green-200 bg-green-50 text-green-800',
    error: 'border-red-200 bg-red-50 text-red-800',
    warning: 'border-amber-200 bg-amber-50 text-amber-800',
    info: 'border-gray-200 bg-white text-gray-700',
  }
  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="fixed right-4 top-4 z-[60] flex w-[min(360px,calc(100vw-32px))] flex-col gap-2">
        {toasts.map(toast => (
          <div key={toast.id} className={`flex items-start gap-2 rounded-lg border px-3 py-2 text-sm shadow-sm ${tones[toast.tone] || tones.info}`}>
            <span className="mt-0.5 flex-shrink-0">{icons[toast.tone] || icons.info}</span>
            <span className="min-w-0 flex-1">{toast.message}</span>
            <button onClick={() => setToasts(items => items.filter(item => item.id !== toast.id))} className="text-current opacity-50 hover:opacity-80">
              <X size={14} />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast() {
  const value = useContext(ToastContext)
  if (!value) return { success: () => {}, error: () => {}, info: () => {} }
  return value
}

export function ConfirmDialog({ title, message, confirmLabel = 'Confirm', danger = false, busy = false, onCancel, onConfirm }) {
  return (
    <Modal
      title={title}
      onClose={onCancel}
      footer={(
        <>
          <Button variant="secondary" onClick={onCancel} disabled={busy}>Cancel</Button>
          <Button variant={danger ? 'danger' : 'primary'} onClick={onConfirm} disabled={busy}>
            {busy ? 'Working...' : confirmLabel}
          </Button>
        </>
      )}
    >
      <p className="text-sm leading-6 text-gray-600">{message}</p>
    </Modal>
  )
}
