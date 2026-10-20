import { useRef, useState, type FormEvent } from 'react'
import { apiRequest } from '../../api/client'
import type { BrowserResearchSubmission, WorkflowCapabilities } from '../../api/generated/types.gen'

export function ResearchForm({ disabled, onTask, capabilities, capabilityError }: {
  disabled: boolean; onTask: (id: string) => void; capabilities: WorkflowCapabilities | null; capabilityError: string
}) {
  const [filename, setFilename] = useState('')
  const [selected, setSelected] = useState<string[]>([])
  const [required, setRequired] = useState(2)
  const [busy, setBusy] = useState(false)
  const [uncertain, setUncertain] = useState(false)
  const [error, setError] = useState('')
  const lock = useRef(false)
  const pending = useRef<{ id: string; body: BrowserResearchSubmission } | null>(null)
  const capability = capabilities?.browser_research
  const unavailable = !capability?.enabled || capabilities?.stopped || capabilities?.resource_blocked
  const reason = capabilityError || (!capability ? 'Checking browser availability…' : !capability.enabled ? capability.reason : capabilities?.stopped ? 'Service stopped. Restart before new work.' : capabilities?.resource_blocked ? 'Local resource checks are blocking new work. See dependency readiness.' : '')
  async function submit(event: FormEvent) {
    event.preventDefault()
    if (lock.current || disabled || unavailable) return
    if (!pending.current) {
      const ids = selected.filter(id => capability!.source_ids.includes(id))
      if (!/^[A-Za-z0-9][A-Za-z0-9_-]{0,63}\.json$/.test(filename) || ids.length < required) {
        setError('Choose enough bundled sources and a new .json basename using letters, numbers, underscores or hyphens.')
        return
      }
      pending.current = { id: crypto.randomUUID(), body: { filename, source_ids: ids, required_sources: required } }
    }
    lock.current = true; setBusy(true); setError('')
    try {
      const intent = pending.current
      const result = await apiRequest('POST /api/workflows/browser-research', { requestId: intent.id, body: intent.body })
      pending.current = null; setUncertain(false); setFilename(''); setSelected([]); onTask(result.task_id)
    } catch (failure) {
      setUncertain(true)
      setError(failure instanceof Error ? failure.message : 'Submission outcome is uncertain.')
    } finally { lock.current = false; setBusy(false) }
  }
  const frozen = disabled || unavailable || busy || uncertain
  return <section className="service-card" aria-label="Bundled browser research">
    <h2>Research bundled sources</h2>
    <p>Choose from the local fixture catalog. Reports contain observed source references and verified text. Public websites are unavailable.</p>
    {reason && <p role="status">{reason}</p>}
    <form onSubmit={event => void submit(event)}>
      <label htmlFor="research-name">New report filename</label>
      <input id="research-name" value={filename} required disabled={frozen} onChange={event => setFilename(event.target.value)} />
      <fieldset disabled={frozen}><legend>Bundled sources</legend>
        {(capability?.source_ids ?? []).map(id => <label key={id}><input type="checkbox" value={id} checked={selected.includes(id)} onChange={event => setSelected(old => event.target.checked ? [...old, id] : old.filter(item => item !== id))} />{id}{id === 'redirect-a' ? ' (alias of source-a)' : ''}</label>)}
      </fieldset>
      <label htmlFor="research-count">Required distinct sources</label>
      <select id="research-count" value={required} disabled={frozen} onChange={event => setRequired(Number(event.target.value))}><option value={1}>1</option><option value={2}>2</option></select>
      <button disabled={disabled || unavailable || busy || !filename || selected.length < required}>{busy ? 'Submitting research…' : uncertain ? 'Retry same research' : 'Create research report'}</button>
    </form>
    {error && <p role="alert">{error}{uncertain && ' Retry preserves the exact source list, destination and request identity.'}</p>}
  </section>
}
