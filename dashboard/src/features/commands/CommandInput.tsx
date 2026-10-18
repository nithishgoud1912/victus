import { useState, useRef, type FormEvent } from 'react'
import { apiRequest } from '../../api/client'
import type { WorkflowCapabilities } from '../../api/generated/types.gen'
import { ChecklistForm } from './ChecklistForm'
import { TextCommandForm } from './TextCommandForm'
export function CommandInput(props: { disabled: boolean; onTask: (id: string) => void; capabilities: WorkflowCapabilities | null; capabilityError: string }) {
 return <><TextCommandForm disabled={props.disabled} onTask={props.onTask} capabilities={props.capabilities}/><NoteInput disabled={props.disabled} onTask={props.onTask}/><ChecklistForm {...props}/></>
}
function NoteInput({ disabled, onTask }: { disabled: boolean; onTask: (id: string) => void }) {
 const [filename, setFilename] = useState(''); const [text, setText] = useState(''); const [busy, setBusy] = useState(false); const [error, setError] = useState(''); const lock = useRef(false); const [uncertain, setUncertain] = useState(false)
 // Keep an uncertain submission bound to the same idempotency key and payload.
 const pending = useRef<{ id: string; filename: string; text: string } | null>(null)
 async function submit(e: FormEvent) { e.preventDefault(); if (lock.current || disabled || !filename.trim() || !text.trim()) return
 lock.current = true; setBusy(true); setError('')
 pending.current ??= { id: crypto.randomUUID(), filename, text }
 try { const p = pending.current; const result = await apiRequest('POST /api/tasks', { requestId: p.id, body: { tool: 'fs.create_note', arguments: { filename: p.filename, text: p.text } } }); onTask(result.task_id); pending.current = null; setUncertain(false); setText('') }
 catch (e) { setUncertain(true); setError(e instanceof Error ? e.message : 'Submission failed. Retry sends the same request.') }
 finally { lock.current = false; setBusy(false) } }
 return <section className="service-card"><h2>Create a note</h2><p>The current backend supports note creation. Review the filename and text before submitting.</p><form onSubmit={submit}><label htmlFor="note-name">Filename</label><input id="note-name" required value={filename} disabled={busy || uncertain || disabled} onChange={e => setFilename(e.target.value)} /><label htmlFor="note-text">Command text / note content</label><textarea id="note-text" required value={text} disabled={busy || uncertain || disabled} onChange={e => setText(e.target.value)} /><button disabled={busy || disabled || !filename.trim() || !text.trim()}>{busy ? 'Submitting…' : uncertain ? 'Retry same submission' : 'Create note'}</button></form>{error && <p role="alert">{error}</p>}</section>
}
