import { useRef, useState } from 'react'
import { apiRequest } from '../api/client'
export function EmergencyStop({ onStop }: { onStop: () => void }) { const lock = useRef(false); const [busy,setBusy] = useState(false); const [error,setError] = useState('')
 async function stop() { if(lock.current) return; lock.current=true; setBusy(true); try { await apiRequest('POST /api/stop'); onStop() } catch(e) { setError(e instanceof Error ? e.message : 'Stop failed') } finally {lock.current=false;setBusy(false)} }
 return <div className="emergency-stop"><button onClick={() => void stop()} disabled={busy}>{busy ? 'Stopping…' : 'Stop all work'}</button>{error && <p role="alert">{error}</p>}</div> }
