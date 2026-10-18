import { checklistItems } from './checklistInput'
import { useRef, useState, type FormEvent } from 'react'
import { apiRequest } from '../../api/client'
import type { NotepadChecklistSubmission, WorkflowCapabilities } from '../../api/generated/types.gen'

export function ChecklistForm({ disabled, onTask, capabilities, capabilityError }: {
  disabled: boolean; onTask: (id: string) => void; capabilities: WorkflowCapabilities | null; capabilityError: string
}) {
  const [filename, setFilename] = useState('')
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [uncertain, setUncertain] = useState(false)
  const lock = useRef(false)
  const pending = useRef<{ id: string; body: NotepadChecklistSubmission } | null>(null)
  const capability = capabilities?.notepad_checklist
  const unavailable = !capability?.enabled || !capability.profiles.length || capabilities?.stopped || capabilities?.resource_blocked
  const reason = capabilityError || (!capability ? 'Checking checklist availability…' : !capability.enabled ? capability.reason : capabilities?.stopped ? 'Service stopped. Restart before submitting.' : capabilities?.resource_blocked ? 'Temporarily unavailable because local resources are low.' : '')

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (lock.current || disabled || unavailable) return
    if (!pending.current) {
      try {
        if (!/^[A-Za-z0-9][A-Za-z0-9_-]{0,63}\.txt$/.test(filename)) throw new Error('Use a new .txt basename with letters, numbers, underscores or hyphens.')
        pending.current = { id: crypto.randomUUID(), body: { profile: capability!.profiles[0]!, filename, items: checklistItems(text) } }
      } catch (failure) { setError(failure instanceof Error ? failure.message : 'Check the checklist.'); return }
    }
    lock.current = true; setBusy(true); setError('')
    try {
      const intent = pending.current
      const result = await apiRequest('POST /api/workflows/notepad-checklist', { requestId: intent.id, body: intent.body })
      pending.current = null; setUncertain(false); setText(''); onTask(result.task_id)
    } catch (failure) {
      setUncertain(true)
      setError(failure instanceof Error ? failure.message : 'Submission outcome is uncertain. Retry keeps the same request.')
    } finally { lock.current = false; setBusy(false) }
  }

  return <section className="service-card" aria-label="Notepad checklist">
    <h2>Create a Notepad checklist</h2><p>Write one item per line. Review the exact Save action before VICTUS saves a new file.</p>
    {reason && <p role="status">{reason}</p>}
    <form onSubmit={event => void submit(event)}>
      <label htmlFor="checklist-name">Checklist filename</label><input id="checklist-name" required value={filename} disabled={disabled || unavailable || busy || uncertain} onChange={event => setFilename(event.target.value)} />
      <label htmlFor="checklist-items">Checklist items, one per line</label><textarea id="checklist-items" required value={text} disabled={disabled || unavailable || busy || uncertain} onChange={event => setText(event.target.value)} />
      <button disabled={disabled || unavailable || busy || !filename || !text}>{busy ? 'Submitting checklist…' : uncertain ? 'Retry same checklist' : 'Create checklist'}</button>
    </form>{error && <p role="alert">{error}{uncertain && ' Retry sends the same filename, items and request identity.'}</p>}
  </section>
}
