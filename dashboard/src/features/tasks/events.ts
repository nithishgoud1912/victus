export type TaskEvent = { event_id: number; task_id: string; event_type: string; timestamp: string; safe_payload: Record<string, unknown> }
export function parseEvent(frame: string): TaskEvent | null {
 const data = frame.split('\n').filter(line => line.startsWith('data:')).map(line => line.slice(5).trimStart()).join('\n')
 if (!data) return null
 const e = JSON.parse(data) as TaskEvent
 if (!Number.isSafeInteger(e.event_id) || e.event_id < 0 || typeof e.task_id !== 'string' || typeof e.event_type !== 'string' || !e.safe_payload || typeof e.safe_payload !== 'object') throw new Error('Invalid task event')
 return e
}
export function mergeEvents(events: TaskEvent[], event: TaskEvent) { if (event.event_type === 'task.snapshot' || events.some(e => e.event_id === event.event_id)) return events; return [...events, event].sort((a,b) => a.event_id-b.event_id).slice(-200) }
