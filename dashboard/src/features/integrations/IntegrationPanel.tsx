import { useEffect, useRef, useState } from 'react'
import { apiRequest } from '../../api/client'
import type { IntegrationStatus, TransferPreview } from '../../api/generated/types.gen'

export function IntegrationPanel({ stopped }: { stopped: boolean }) {
  const [status, setStatus] = useState<IntegrationStatus | null>(null)
  const [prompt, setPrompt] = useState('')
  const [preview, setPreview] = useState<TransferPreview | null>(null)
  const [expires, setExpires] = useState(0)
  const [now, setNow] = useState(() => Date.now())
  const [result, setResult] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const lock = useRef(false)
  const previewBody = useRef<HTMLPreElement>(null)

  useEffect(() => {
    const abort = new AbortController()
    let timer: ReturnType<typeof setTimeout>
    async function poll() {
      try { setStatus(await apiRequest('GET /api/integrations', { signal: abort.signal })) }
      catch (failure) { if (!abort.signal.aborted) setError(failure instanceof Error ? failure.message : 'Integration status unavailable.') }
      finally { if (!abort.signal.aborted) timer = setTimeout(() => void poll(), 2000) }
    }
    void poll()
    return () => { abort.abort(); clearTimeout(timer) }
  }, [])
  useEffect(() => {
    if (!preview) return
    const timer = setInterval(() => setNow(Date.now()), 250)
    previewBody.current?.focus()
    return () => clearInterval(timer)
  }, [preview])

  async function act(work: () => Promise<void>) {
    if (lock.current) return
    lock.current = true
    setBusy(true)
    setError('')
    try { await work() }
    catch (failure) { setError(failure instanceof Error ? failure.message : 'Integration unavailable.') }
    finally { lock.current = false; setBusy(false) }
  }

  return <section className="service-card" aria-labelledby="integration-title">
    <h2 id="integration-title">Optional integrations</h2>
    <p>MCP notes: {status?.mcp_notes ? 'Enabled for workspace notes only' : 'Disabled'}. Cloud: {status?.cloud ?? 'Checking…'}.</p>
    {status?.cloud_pin && <>
      <p>This separate cloud request returns text for review. It cannot run a computer action. It sends data through OpenRouter to {status.upstream}.</p>
      <form onSubmit={event => { event.preventDefault(); void act(async () => {
        const next = await apiRequest('POST /api/integrations/cloud/preview', { body: {
          pin: status.cloud_pin!, messages: [{ role: 'user', content: prompt }],
          output_schema: { type: 'object', properties: { summary: { type: 'string' } }, required: ['summary'], additionalProperties: false },
          max_output_tokens: 512, context_tokens: 4096, structured_path: 'json_schema',
        } })
        setPreview(next); setExpires(Date.now() + next.expires_in_seconds * 1000); setNow(Date.now()); setResult('')
      }) }}>
        <label htmlFor="cloud-prompt">Text to propose for transfer</label>
        <textarea id="cloud-prompt" value={prompt} maxLength={32768} required disabled={busy || !!preview || stopped} onChange={event => setPrompt(event.target.value)} />
        <button disabled={busy || stopped || !!preview || !prompt.trim()}>Preview transfer</button>
      </form>
    </>}
    {preview && !stopped && <section aria-label="Exact cloud transfer preview">
      <p>Recipient: {preview.recipient}</p>
      <p role="status">{now >= expires ? 'Expired. Deny and create a new preview.' : `Expires in ${Math.max(0, Math.ceil((expires - now) / 1000))} seconds.`}</p>
      <pre ref={previewBody} tabIndex={0} aria-label="Exact request body">{preview.body}</pre>
      <p>Request checksum: {preview.sha256}</p>
      <button disabled={busy} onClick={() => void act(async () => {
        const id = preview.id; setPreview(null)
        await apiRequest('POST /api/integrations/cloud/review', { body: { id, approve: false, confirmation: 'explicit_user_review' } })
        setStatus(current => current && { ...current, cloud: 'consent_denied' })
      })}>Deny transfer</button>
      <button disabled={busy || stopped || now >= expires} onClick={() => void act(async () => {
        const id = preview.id; setPreview(null)
        const next = await apiRequest('POST /api/integrations/cloud/review', { body: { id, approve: true, confirmation: 'explicit_user_review' } })
        setResult(next.response?.content ?? '')
        setPrompt('')
      })}>Approve this transfer once</button>
    </section>}
    {result && <><p>Cloud response — review before use:</p><pre tabIndex={0}>{result}</pre></>}
    {error && <p role="alert">{error}</p>}
  </section>
}
