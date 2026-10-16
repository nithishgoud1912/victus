import type { TaskEvent } from './events'
export function TaskTimeline({ events }: { events: TaskEvent[] }) { return <section className="service-card"><h2>Task progress</h2><ol>{events.map(e => <li key={e.event_id}><span>{e.event_type}</span> <small>#{e.event_id} · {e.timestamp}</small></li>)}</ol>{!events.length && <p>Waiting for backend events.</p>}</section> }
