import { useRef, useState, type FormEvent } from 'react'
import { apiRequest, ApiError } from '../../api/client'
import type { CommandFields, CommandResponse, WorkflowCapabilities } from '../../api/generated/types.gen'

export function TextCommandForm({ disabled, onTask, capabilities }: { disabled: boolean; onTask: (id: string) => void; capabilities: WorkflowCapabilities | null }) {
  const [text, setText] = useState('')
  const [result, setResult] = useState<CommandResponse | null>(null)
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [resumeId, setResumeId] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const lock = useRef(false)
  const pending = useRef<{ id: string; body: { text: string } } | null>(null)
  const clarification = useRef<CommandFields | null>(null)
  const [uncertain, setUncertain] = useState(false)
  const [retryCommand, setRetryCommand] = useState(false)

  async function perform(action: () => Promise<CommandResponse>) {
    if (lock.current || disabled) return
    lock.current = true; setBusy(true); setError('')
    try {
      const value = await action()
      setResult(value); setResumeId(value.command_id); setUncertain(false)
      pending.current = null; clarification.current = null
      if (value.state === 'submitted' && value.task_id) onTask(value.task_id)
    } catch (e) {
      if (e instanceof ApiError && e.status === 422) {
        pending.current = null; clarification.current = null
      }
      setRetryCommand(pending.current !== null)
      setUncertain(pending.current !== null || clarification.current !== null); setError(e instanceof Error ? e.message : 'Request failed. Retry preserves the same command.')
    } finally { lock.current = false; setBusy(false) }
  }
  function submit(event: FormEvent) {
    event.preventDefault()
    if (lock.current || disabled) return
    if (!pending.current) {
      setResult(null); setAnswers({})
      pending.current = { id: crypto.randomUUID(), body: { text } }
    }
    const value = pending.current
    void perform(() => apiRequest('POST /api/commands', { requestId: value.id, body: value.body }))
  }
  function clarify(event: FormEvent) {
    event.preventDefault()
    if (!result) return
    const fields: CommandFields = {}
    for (const name of result.missing ?? []) {
      const value = answers[name] ?? ''
      if (name === 'items') fields.items = value.split('\n').filter(line => line.trim())
      else if (name === 'source_ids') fields.source_ids = value.split(',').map(line => line.trim()).filter(Boolean)
      else if (name === 'required_sources') fields.required_sources = Number(value)
      else if (name === 'intent') fields.intent = value as CommandFields['intent']
      else if (name === 'filename') fields.filename = value
      else if (name === 'content') fields.content = value
    }
    clarification.current ??= fields
    void perform(() => apiRequest('POST /api/commands/{command_id}/clarify', {
      path: { command_id: result.command_id }, body: clarification.current!,
    }))
  }
  return <section className="service-card"><h2>Describe a supported task</h2>
    <p>Create a note, a qualified Notepad checklist, or research the bundled sources source-a and source-b. Public websites are unavailable. Missing details require an explicit response before work begins.</p>
    <p>Example: Create a note hello.txt containing &quot;Hello&quot;</p>
    <p role="status">{capabilities?.browser_research?.enabled ? 'Bundled fixture research is available.' : capabilities?.browser_research?.reason ?? 'Browser readiness has not been confirmed.'}</p>
    <p>{capabilities?.commands?.reason ?? 'Text commands use confirmed deterministic workflows.'}</p>
    <form onSubmit={submit}>
      <label htmlFor="task-command">Task description</label>
      <textarea id="task-command" required maxLength={4096} value={text} disabled={disabled || busy || uncertain} onChange={e => setText(e.target.value)} />
      <button disabled={disabled || busy || !text.trim() || (uncertain && !retryCommand)}>{busy ? 'Working…' : uncertain && retryCommand ? 'Retry same command' : 'Submit command'}</button>
    </form>
    <form onSubmit={e => { e.preventDefault(); if (/^[a-f0-9]{32}$/.test(resumeId)) void perform(() => apiRequest('GET /api/commands/{command_id}', { path: { command_id: resumeId } })) }}>
      <label htmlFor="resume-command">Saved command ID</label>
      <input id="resume-command" value={resumeId} pattern="[a-f0-9]{32}" maxLength={32} required disabled={disabled || busy || uncertain} onChange={e => setResumeId(e.target.value)} />
      <button disabled={disabled || busy || uncertain || !/^[a-f0-9]{32}$/.test(resumeId)}>Check saved command</button>
    </form>
    {result && <div aria-live="polite"><p>{result.message}</p><p>Command ID: <code>{result.command_id}</code></p>
      {result.state === 'clarification' && <form onSubmit={clarify}>
        {(result.missing ?? []).map(name => <div key={name}><label htmlFor={'answer-' + name}>{({ intent: 'Task type', filename: 'New filename', content: 'Literal note text', items: 'Checklist items, one per line', source_ids: 'Reviewed source IDs, separated by commas', required_sources: 'Required distinct sources' } as Record<string, string>)[name] ?? name}</label>
          {name === 'intent' ? <select id={'answer-' + name} required disabled={disabled || busy || uncertain} value={answers[name] ?? ''} onChange={e => setAnswers({ ...answers, [name]: e.target.value })}><option value="">Choose a task</option><option value="note">Note</option><option value="checklist">Notepad checklist</option><option value="research">Fixture research</option></select> :
            <textarea id={'answer-' + name} required maxLength={8192} disabled={disabled || busy || uncertain} value={answers[name] ?? ''} onChange={e => setAnswers({ ...answers, [name]: e.target.value })} />}</div>)}
        <button disabled={disabled || busy}>{uncertain ? 'Retry same response' : 'Continue command'}</button>
      </form>}
    </div>}
    {error && <p role="alert">{error}</p>}
  </section>
}
