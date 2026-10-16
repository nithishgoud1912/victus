import { useEffect, useRef, useState } from 'react'
import { apiRequest } from '../../api/client'
import type { DiagnosticPreview, MemoryEntry, MemoryInput } from '../../api/generated/types.gen'

export function MemoryPanel() {
  const [entries, setEntries] = useState<MemoryEntry[]>([])
  const [value, setValue] = useState('')
  const [kind, setKind] = useState<'preference' | 'summary'>('preference')
  const [editing, setEditing] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [preview, setPreview] = useState<DiagnosticPreview | null>(null)
  const [exported, setExported] = useState('')
  const lock = useRef(false)

  useEffect(() => {
    const abort = new AbortController()
    void apiRequest('GET /api/memory', { signal: abort.signal }).then(items => {
      if (!abort.signal.aborted) setEntries(items)
    }).catch(failure => { if (!abort.signal.aborted) setError(failure.message) })
    return () => abort.abort()
  }, [])

  async function act(action: () => Promise<void>) {
    if (lock.current) return
    lock.current = true
    setBusy(true)
    setError('')
    try { await action() }
    catch (failure) { setError(failure instanceof Error ? failure.message : 'Memory request failed.') }
    finally { lock.current = false; setBusy(false) }
  }

  async function save() {
    const body: MemoryInput = {
      type: kind, value, confirmation: 'explicit_user_review',
      provenance: kind === 'preference' ? 'explicit_user_preference' : 'user_reviewed_summary',
    }
    if (editing) await apiRequest('POST /api/memory/{memory_id}', { path: { memory_id: editing }, body })
    else await apiRequest('POST /api/memory', { body })
    setEntries(await apiRequest('GET /api/memory'))
    setEditing(null)
    setValue('')
  }

  return <details className="service-card">
    <summary>Memory and diagnostics</summary>
    <h2>Reviewed memory</h2>
    <p>Only save preferences or summaries you have reviewed. Current instructions and safety policy take priority. For planning preferences, use language=, tone=, date_format= or preferred_editor=.</p>
    <form onSubmit={event => { event.preventDefault(); if (value.trim()) void act(save) }}>
      <label htmlFor="memory-kind">Memory type</label>
      <select id="memory-kind" value={kind} onChange={event => setKind(event.target.value as 'preference' | 'summary')} disabled={busy}>
        <option value="preference">Explicit preference</option><option value="summary">Reviewed summary</option>
      </select>
      <label htmlFor="memory-value">Reviewed memory value</label>
      <textarea id="memory-value" required maxLength={8192} value={value} onChange={event => setValue(event.target.value)} disabled={busy} />
      <button disabled={busy || !value.trim()}>{editing ? 'Save reviewed edit' : 'Remember reviewed value'}</button>
    </form>
    <ul>{entries.map(entry => <li key={entry.memory_id}>
      <p>{entry.value}</p><small>{entry.type} · {entry.provenance}</small>
      <div className="session-controls">
        <button disabled={busy} onClick={() => { setEditing(entry.memory_id); setKind(entry.type); setValue(entry.value) }}>Edit memory</button>
        <button disabled={busy} onClick={() => void act(async () => {
          await apiRequest('DELETE /api/memory/{memory_id}', { path: { memory_id: entry.memory_id } })
          setEntries(await apiRequest('GET /api/memory'))
          if (editing === entry.memory_id) { setEditing(null); setValue('') }
        })}>Forget memory</button>
      </div>
    </li>)}</ul>
    <div className="session-controls">
      <button disabled={busy} onClick={() => void act(async () => setExported(JSON.stringify(await apiRequest('GET /api/memory/export'), null, 2)))}>Review memory export</button>
      <button disabled={busy} onClick={() => void act(async () => setPreview(await apiRequest('GET /api/diagnostics/preview')))}>Review redacted diagnostics</button>
    </div>
    {exported && <pre tabIndex={0} aria-label="Memory export preview">{exported}</pre>}
    {preview && <><pre tabIndex={0} aria-label="Diagnostic export preview">{preview.contents}</pre>
      <button disabled={busy} onClick={() => void act(async () => {
        const result = await apiRequest('POST /api/diagnostics/export', { body: {
          preview_id: preview.preview_id, sha256: preview.sha256, confirmation: 'explicit_user_review',
        } })
        const url = URL.createObjectURL(new Blob([result.contents], { type: 'application/json' }))
        const anchor = document.createElement('a'); anchor.href = url; anchor.download = 'victus-diagnostics.json'; anchor.click()
        setTimeout(() => URL.revokeObjectURL(url), 1000)
        setPreview(null)
      })}>Download reviewed diagnostics</button></>}
    {error && <p role="alert">{error}</p>}
  </details>
}
