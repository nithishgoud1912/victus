import { describe, expect, it } from 'vitest'
import { mergeEvents, parseEvent } from './events'
const event = { event_id: 4, task_id: 't', event_type: 'task.started', timestamp: 'now', safe_payload: {} }
describe('backend event replay', () => {
 it('parses named SSE with multiline data and ignores heartbeat', () => { expect(parseEvent(': ping')).toBeNull(); expect(parseEvent(`id: 4\nevent: task.started\ndata: ${JSON.stringify(event)}`)).toEqual(event) })
 it('deduplicates replay and orders progress', () => { expect(mergeEvents([event],event)).toEqual([event]); expect(mergeEvents([event],{...event,event_id:2}).map(e=>e.event_id)).toEqual([2,4]) })
 it('keeps snapshots separate even when IDs match', () => { expect(mergeEvents([event],{...event,event_type:'task.snapshot'})).toEqual([event]) })
 it('rejects malformed authoritative event IDs', () => { expect(()=>parseEvent('data: {"event_id":-1}')).toThrow() })
})
