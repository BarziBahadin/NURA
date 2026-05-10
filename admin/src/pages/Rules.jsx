import React, { useState, useEffect } from 'react'
import { api } from '../App.jsx'

export default function Rules() {
  const [rules, setRules] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [search, setSearch] = useState('')
  const [expanded, setExpanded] = useState(null)

  useEffect(() => {
    async function load() {
      setLoading(true)
      setError(null)
      try {
        const res = await fetch(`${api.base}/rules`, {
          headers: { Authorization: `Bearer ${api.key}` },
        })
        if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
        const data = await res.json()
        setRules(data.rules || [])
        setTotal(data.total || 0)
      } catch (e) {
        setError(e.message)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  const filtered = rules.filter(r =>
    r.title.toLowerCase().includes(search.toLowerCase()) ||
    r.keywords.some(k => k.includes(search))
  )

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Rules Engine</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Layer 0 — keyword-based article matching (runs before ML & OpenAI)
          </p>
        </div>
        {!loading && (
          <span className="bg-blue-100 text-blue-700 text-sm font-semibold px-3 py-1 rounded-full">
            {total} rules loaded
          </span>
        )}
      </div>

      <div className="mb-4">
        <input
          type="text"
          placeholder="Search by title or keyword…"
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="w-full max-w-sm border border-gray-200 rounded-xl px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
        />
      </div>

      {loading && (
        <div className="flex items-center justify-center h-48 text-gray-400 text-sm">
          Loading rules…
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-xl p-4 text-sm">
          Failed to load rules: {error}
        </div>
      )}

      {!loading && !error && filtered.length === 0 && (
        <div className="flex items-center justify-center h-48 text-gray-400 text-sm">
          {search ? 'No rules match your search.' : 'No rules loaded — check articals.json in .manafest/'}
        </div>
      )}

      {!loading && !error && (
        <div className="space-y-3">
          {filtered.map((rule, i) => (
            <div
              key={rule.title}
              className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden"
            >
              <button
                className="w-full flex items-center justify-between px-5 py-4 text-left hover:bg-gray-50 transition-colors"
                onClick={() => setExpanded(expanded === i ? null : i)}
              >
                <div className="flex items-center gap-3 min-w-0">
                  <span className="flex-shrink-0 w-7 h-7 rounded-lg bg-blue-50 text-blue-600 text-xs font-bold flex items-center justify-center">
                    {i + 1}
                  </span>
                  <span className="font-medium text-gray-800 truncate">{rule.title}</span>
                </div>
                <div className="flex items-center gap-3 flex-shrink-0 ml-4">
                  <span className="text-xs text-gray-400">{rule.keyword_count} keywords</span>
                  <svg
                    className={`w-4 h-4 text-gray-400 transition-transform duration-200 ${expanded === i ? 'rotate-180' : ''}`}
                    fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                  </svg>
                </div>
              </button>

              {expanded === i && (
                <div className="border-t border-gray-100 px-5 pb-5 pt-4">
                  <div className="mb-4">
                    <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                      Matched Keywords (root tokens, up to 20)
                    </h3>
                    <div className="flex flex-wrap gap-1.5">
                      {rule.keywords.map(kw => (
                        <span
                          key={kw}
                          className="bg-blue-50 text-blue-700 text-xs px-2 py-0.5 rounded-lg font-mono"
                          dir="rtl"
                        >
                          {kw}
                        </span>
                      ))}
                      {rule.keyword_count > 20 && (
                        <span className="text-xs text-gray-400 px-2 py-0.5">
                          +{rule.keyword_count - 20} more
                        </span>
                      )}
                    </div>
                  </div>
                  <div>
                    <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                      Response Preview
                    </h3>
                    <p
                      className="text-sm text-gray-700 bg-gray-50 rounded-xl p-3 leading-relaxed whitespace-pre-wrap"
                      dir="rtl"
                    >
                      {rule.response_preview}
                      {rule.response_preview.length >= 300 && (
                        <span className="text-gray-400"> …</span>
                      )}
                    </p>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
