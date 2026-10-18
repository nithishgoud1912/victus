import { useEffect, useRef, useState } from 'react'
import { apiRequest } from '../../api/client'
import type { VoiceSnapshot, CommandFields, CommandSubmission } from '../../api/generated/types.gen'

export function VoicePanel({ stopped }: { stopped: boolean }) {
  const [voice, setVoice] = useState<VoiceSnapshot | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const lock = useRef(false)
  const acknowledged = useRef('')

  function receive(next: VoiceSnapshot) {
    setVoice(previous => !previous || (next.revision ?? 0) >= (previous.revision ?? 0) ? next : previous)
  }

  useEffect(() => {
    const abort = new AbortController()
    let timer: ReturnType<typeof setTimeout>
    async function poll() {
      try {
        const snapshot = await apiRequest('GET /api/voice', { signal: abort.signal })
        if (!abort.signal.aborted) receive(snapshot)
      } catch (failure) {
        if (!abort.signal.aborted) setError(failure instanceof Error ? failure.message : 'Voice status unavailable.')
      } finally {
        if (!abort.signal.aborted) timer = setTimeout(() => void poll(), 350)
      }
    }
    void poll()
    return () => { abort.abort(); clearTimeout(timer) }
  }, [])

  // Effects run after this revision's summary has been committed to the UI.
  // This acknowledges display only; it never approves or submits an action.
  useEffect(() => {
    if (!voice?.speech_pending || voice.muted || !voice.session_id || !voice.summary) return
    const key = `${voice.session_id}:${voice.revision}`
    if (acknowledged.current === key) return
    acknowledged.current = key
    void apiRequest('POST /api/voice/displayed', {
      body: { session_id: voice.session_id, revision: voice.revision ?? 0 },
    }).then(receive).catch(failure => setError(failure.message))
  }, [voice])

  async function act(action: () => Promise<VoiceSnapshot>) {
    if (lock.current) return
    lock.current = true
    setBusy(true)
    setError('')
    try { receive(await action()) }
    catch (failure) { setError(failure instanceof Error ? failure.message : 'Voice request failed.') }
    finally { lock.current = false; setBusy(false) }
  }

  const session = { session_id: voice?.session_id ?? '', revision: voice?.revision ?? 0 }
  const canRecord = voice?.enabled && ['idle', 'error'].includes(voice.state) && !voice.wake_suppressed
  return (
    <section className="service-card" aria-labelledby="voice-title">
      <h2 id="voice-title">Push to talk</h2>
      <p>Record with your Python microphone. Finish recording, then review the transcript and exact note fields before submitting.</p>
      <p role="status">Voice: {voice?.state ?? 'Checking…'}</p>
      <p role="status">Wake word: {voice?.wake_listening ? 'Listening on this microphone' : voice?.wake_available ? 'Off or paused during voice work' : 'Needs a qualified local model'}</p>
      {voice && !voice.enabled && <p>Set a downloaded local STT model path on the backend to enable recording.</p>}
      <div className="session-controls">
        <button disabled={busy || stopped || !voice?.wake_available} onClick={() => void act(() => apiRequest('POST /api/voice/wake/enable'))}>Enable wake listening</button>
        <button disabled={busy || !voice?.wake_available} onClick={() => void act(() => apiRequest('POST /api/voice/wake/disable'))}>Disable wake listening</button>
        <button disabled={busy || stopped || !canRecord} onClick={() => void act(() => apiRequest('POST /api/voice/start'))}>Start recording</button>
        <button disabled={busy || voice?.state !== 'recording'} onClick={() => void act(() => apiRequest('POST /api/voice/finish', { body: session }))}>Finish recording</button>
        <button disabled={busy || !voice || voice.state === 'idle'} onClick={() => void act(() => apiRequest('POST /api/voice/cancel'))}>Cancel voice / interrupt speech</button>
        <button disabled={busy || !voice} onClick={() => void act(() => apiRequest('POST /api/voice/mute', { body: { muted: !voice?.muted } }))}>{voice?.muted ? 'Unmute spoken results' : 'Mute spoken results'}</button>
      </div>
      {voice?.state === 'reviewing' && <ReviewedVoiceForm key={voice.session_id} voice={voice} busy={busy} stopped={stopped} submitCommand={command => void act(() => apiRequest('POST /api/voice/submit', { body: { ...session, confirmation: 'explicit_user_review', command } }))} submit={(filename, text) => void act(() => apiRequest('POST /api/voice/submit', { body: {
        ...session, confirmation: 'explicit_user_review',
        action: { tool: 'fs.create_note', arguments: { filename, text } },
      } }))} />}
      {voice?.state === 'clarifying' && voice.command && <VoiceClarification key={voice.command.command_id + ':' + voice.command.missing?.join(',')} voice={voice} busy={busy} stopped={stopped} submit={fields => void act(() => apiRequest('POST /api/voice/clarify', { body: { ...session, confirmation: 'explicit_user_review', fields } }))} />}
      {voice?.task_id && <p>Task: <code>{voice.task_id}</code></p>}
      {voice?.summary && <p aria-live="polite">{voice.summary}</p>}
      {voice?.error_code && <p role="alert">{voice.error_code}</p>}
      {voice?.wake_error && <p role="alert">{voice.wake_error}</p>}
      {error && <p role="alert">{error}</p>}
    </section>
  )
}

function ReviewedVoiceForm({ voice, busy, stopped, submit, submitCommand }: {
  voice: VoiceSnapshot; busy: boolean; stopped: boolean
  submit: (filename: string, text: string) => void
  submitCommand: (command: CommandSubmission) => void
}) {
  const [filename, setFilename] = useState(voice.proposal?.arguments.filename ?? '')
  const [text, setText] = useState(voice.proposal?.arguments.text ?? '')
  const [mode, setMode] = useState(voice.proposal ? 'note' : 'command')
  const [command, setCommand] = useState(voice.transcript?.text ?? '')
  const [locked, setLocked] = useState(false)
  return <form onSubmit={event => {
    event.preventDefault()
    setLocked(true)
    if (mode === 'command' && command.trim()) submitCommand({ text: command })
    else if (filename.trim() && text.trim()) submit(filename, text)
  }}>
    <label htmlFor="voice-transcript">Recognized transcript</label>
    <pre id="voice-transcript" tabIndex={0}>{voice.transcript?.text}</pre>
    {voice.clarification && <p role="status">{voice.clarification}</p>}
    <label htmlFor="voice-mode">Review as</label>
    <select id="voice-mode" value={mode} disabled={busy || locked} onChange={e => setMode(e.target.value)}><option value="note">Note</option><option value="command">Supported command</option></select>
    {mode === 'command' ? <><label htmlFor="voice-command">Reviewed command</label><textarea id="voice-command" required maxLength={4096} value={command} onChange={e => setCommand(e.target.value)} disabled={busy || locked}/><p>Use the same supported commands as typed input. Missing details ask for clarification. This confirmation does not approve Save.</p></> : <>
    <label htmlFor="voice-filename">Reviewed filename</label>
    <input id="voice-filename" required maxLength={68} pattern="[A-Za-z0-9][A-Za-z0-9_\-]{0,63}\.txt" value={filename} onChange={event => setFilename(event.target.value)} disabled={busy || locked} />
    <label htmlFor="voice-note">Reviewed note text</label>
    <textarea id="voice-note" required maxLength={8192} value={text} onChange={event => setText(event.target.value)} disabled={busy || locked} />
    </>}
    <p>Submitting creates this note through the same task queue as typed input. Review expires after two minutes.</p>
    {locked && !busy && <p role="status">Retry keeps the same reviewed details. Use Stop if the result is uncertain; cancel voice to start a fresh review.</p>}
    <button disabled={busy || stopped || (mode === 'command' ? !command.trim() : !filename.trim() || !text.trim())}>{locked ? 'Retry same reviewed transcript' : 'Submit reviewed transcript'}</button>
  </form>
}

function VoiceClarification({ voice, busy, stopped, submit }: { voice: VoiceSnapshot; busy: boolean; stopped: boolean; submit: (fields: CommandFields) => void }) {
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [locked, setLocked] = useState(false)
  return <form onSubmit={event => {
    event.preventDefault()
    setLocked(true)
    const fields: CommandFields = {}
    for (const name of voice.command?.missing ?? []) {
      const value = answers[name] ?? ''
      if (name === 'intent') fields.intent = value as CommandFields['intent']
      else if (name === 'filename') fields.filename = value
      else if (name === 'content') fields.content = value
      else if (name === 'items') fields.items = value.split('\n').filter(line => line.trim())
      else if (name === 'source_ids') fields.source_ids = value.split(',').map(line => line.trim()).filter(Boolean)
      else if (name === 'required_sources') fields.required_sources = Number(value)
    }
    submit(fields)
  }}><p role="status">{voice.command?.message}</p><p>Saved command ID: <code>{voice.command?.command_id}</code></p>
    {(voice.command?.missing ?? []).map(name => <div key={name}><label htmlFor={'voice-answer-' + name}>{({intent:'Voice task type',filename:'Voice filename',content:'Voice note text',items:'Voice checklist items, one per line',source_ids:'Voice source IDs, separated by commas',required_sources:'Voice distinct source count'} as Record<string,string>)[name] ?? name}</label>
      {name === 'intent' ? <select id={'voice-answer-' + name} required value={answers[name] ?? ''} disabled={busy || stopped || locked} onChange={e => setAnswers({...answers,[name]:e.target.value})}><option value="">Choose</option><option value="note">Note</option><option value="checklist">Notepad checklist</option><option value="research">Fixture research</option></select> : <textarea id={'voice-answer-' + name} required maxLength={8192} value={answers[name] ?? ''} disabled={busy || stopped || locked} onChange={e => setAnswers({...answers,[name]:e.target.value})}/>}</div>)}
    {locked && !busy && <p role="status">Retry keeps the same answers. Use Stop if the result is uncertain; cancel voice to start a fresh review.</p>}
    <button disabled={busy || stopped}>{locked ? 'Retry same voice clarification' : 'Confirm voice clarification'}</button>
  </form>
}
