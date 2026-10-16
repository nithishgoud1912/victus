import { useEffect, useState, type FormEvent } from 'react'
import { ApiError, apiRequest, clearSessionToken, setSessionToken } from './api/client'
import type { HealthResponse } from './api/generated/types.gen'
import './App.css'

function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [entry, setEntry] = useState('')
  const [busy, setBusy] = useState(true)
  const [error, setError] = useState<ApiError | Error | null>(null)

  useEffect(() => {
    const abort = new AbortController()
    async function restore() {
      try {
        await apiRequest('GET /api/session', { signal: abort.signal })
        setHealth(await apiRequest('GET /api/health', { signal: abort.signal }))
      } catch (failure) {
        if (!abort.signal.aborted && failure instanceof ApiError && failure.status !== 401) setError(failure)
      } finally {
        if (!abort.signal.aborted) setBusy(false)
      }
    }
    void restore()
    return () => abort.abort()
  }, [])

  async function connect(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      setSessionToken(entry)
      setEntry('')
      if (!import.meta.env.DEV) {
        await apiRequest('POST /api/session')
        clearSessionToken()
      }
      setHealth(await apiRequest('GET /api/health'))
    } catch (failure) {
      clearSessionToken()
      setError(failure instanceof Error ? failure : new Error('Unable to connect.'))
    } finally {
      setEntry('')
      setBusy(false)
    }
  }

  async function refresh() {
    setBusy(true)
    setError(null)
    try {
      setHealth(await apiRequest('GET /api/health'))
    } catch (failure) {
      if (failure instanceof ApiError && failure.status === 401) setHealth(null)
      setError(failure instanceof Error ? failure : new Error('Unable to refresh.'))
    } finally { setBusy(false) }
  }

  async function disconnect() {
    setBusy(true)
    try { await apiRequest('DELETE /api/session') }
    catch { /* Clear local credentials even when the service is unavailable. */ }
    finally {
      clearSessionToken()
      setHealth(null)
      setEntry('')
      setError(null)
      setBusy(false)
    }
  }

  return (
    <div className="workspace">
      <aside className="sidebar" aria-label="Workspace identity">
        <a className="brand" href="/" aria-label="VICTUS home"><span className="brand-mark">V</span> VICTUS<span className="version">v1</span></a>
        <div className="sidebar-middle"><span className="eyebrow">YOUR WORKSPACE</span><div className="nav-current"><span aria-hidden="true">▦</span> Overview</div></div>
        <div className="sidebar-note"><span className="local-dot" /> Local by design<p>Your assistant.<br />On your computer.</p></div>
      </aside>
      <main>
        <header className="topbar"><span>Workspace / <strong>Overview</strong></span><span className="local-label"><span className="local-dot" /> Local connection</span></header>
        <section className="page-heading"><span className="eyebrow">WELCOME TO VICTUS</span><h1>A little less busywork.<br />A little more possibility.</h1><p>Your local assistant starts with a connection you control.</p></section>
        <div className="dashboard-grid">
          <section className="connection-card" aria-labelledby="connection-title">
            <div className="card-top"><span className="section-number">01 / CONNECTION</span><span className={`status ${health ? 'connected' : ''}`}><span />{health ? 'Connected' : 'Not connected'}</span></div>
            <div className="connection-symbol" aria-hidden="true">↗</div>
            <h2 id="connection-title">{health ? 'Your workspace is connected.' : 'Bring your assistant online.'}</h2>
            <p className="card-copy">{health ? 'Your connection is ready. You can check the local service or end this session below.' : 'Start your local VICTUS service, then paste its session token to connect.'}</p>
            {health ? <div className="session-controls"><button onClick={() => void refresh()} disabled={busy}>{busy ? 'Checking…' : 'Check connection'}<span aria-hidden="true">↗</span></button><button className="secondary" onClick={() => void disconnect()} disabled={busy}>Disconnect</button></div> :
              <form onSubmit={(event) => void connect(event)} autoComplete="off"><label htmlFor="session-token">Session token</label><input id="session-token" name="victus-token" type="password" placeholder="Paste your local session token" autoComplete="off" autoCapitalize="off" spellCheck={false} maxLength={512} value={entry} onChange={(event) => setEntry(event.target.value)} disabled={busy} /><button type="submit" disabled={busy || entry.trim().length < 32}>{busy ? 'Checking connection…' : 'Connect to VICTUS'}<span aria-hidden="true">↗</span></button><p className="input-note">{import.meta.env.DEV ? 'This token stays in memory and clears when you refresh or disconnect.' : 'Your sign-in uses a local browser session. The token is cleared after connecting.'}</p></form>}
            {error && <div className="error" role="alert">{error.message}{error instanceof ApiError && <small>Reference: {error.requestId}</small>}</div>}
          </section>
          <aside className="detail-column" aria-label="Connection details">
            <section className="service-card"><div className="card-top"><span className="section-number">SERVICE STATUS</span><span className="tiny-orbit" aria-hidden="true" /></div><h2>{health ? health.stopped ? 'Service stopped' : 'Ready when you are.' : 'Waiting for you.'}</h2><p>{health ? health.stopped ? 'Restart the local service before starting new tasks.' : 'The local VICTUS service responded successfully.' : 'Connect to see the live status of your local service.'}</p><dl><div><dt>Connection</dt><dd>{health ? 'Authenticated' : 'Disconnected'}</dd></div><div><dt>Runs on</dt><dd>Your computer</dd></div><div><dt>Service</dt><dd>{health ? health.stopped ? 'Stopped' : 'Available' : 'Not checked'}</dd></div></dl></section>
            <section className="quiet-card"><span aria-hidden="true">✧</span><h3>Built around your control.</h3><p>Review consequential actions before they run. Stop work whenever you need to.</p></section>
          </aside>
        </div>
        <footer><span className="local-dot" /> Your connection is private to this local workspace.<span className="footer-mark">VICTUS / 01</span></footer>
      </main>
    </div>
  )
}
export default App
