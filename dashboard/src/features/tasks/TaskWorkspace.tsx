import { MemoryPanel } from '../memory/MemoryPanel'
import { IntegrationPanel } from '../integrations/IntegrationPanel'
import { ApiError } from '../../api/client'
import { VoicePanel } from '../voice/VoicePanel'
import { useEffect, useState } from 'react'
import { apiRequest } from '../../api/client'
import type { HealthResponse, TaskResult as Result } from '../../api/generated/types.gen'
import { EmergencyStop } from '../../components/EmergencyStop'
import { CommandInput } from '../commands/CommandInput'
import { HealthPanel } from '../health/HealthPanel'
import { ApprovalPanel } from '../approvals/ApprovalPanel'
import { TaskResult } from './TaskResult'
import { TaskTimeline } from './TaskTimeline'
import { mergeEvents, parseEvent, type TaskEvent } from './events'
export function TaskWorkspace({ health, onRefresh }: { health: HealthResponse; onRefresh: () => void }) {
 const [tasks,setTasks]=useState<Record<string,Result>>({}); const [events,setEvents]=useState<TaskEvent[]>([]); const [approvals,setApprovals]=useState<string[]>([]); const [error,setError]=useState(''); const [stopped,setStopped]=useState(health.stopped)
 useEffect(()=>{ const abort=new AbortController(); let cursor=0; let retry:ReturnType<typeof setTimeout>; let reader:ReadableStreamDefaultReader<string>|undefined
 async function snapshot(id:string){const task=await apiRequest('GET /api/tasks/{task_id}',{path:{task_id:id},signal:abort.signal});if(!abort.signal.aborted)setTasks(old=>({...old,[id]:task}))}
 async function connect(){ try {
 const response=await apiRequest('GET /api/events',{response:'stream',query:{cursor},signal:abort.signal}); if(!response.body)throw new Error('Event stream unavailable'); setError(''); reader=response.body.pipeThrough(new TextDecoderStream()).getReader(); let buffer=''
 while(!abort.signal.aborted){const chunk=await reader.read();if(chunk.done)break;buffer+=chunk.value.replace(/\r\n/g,'\n');let boundary:number
 while((boundary=buffer.indexOf('\n\n'))>=0){const frame=buffer.slice(0,boundary);buffer=buffer.slice(boundary+2);const e=parseEvent(frame);if(!e)continue
 if(e.event_type!=='task.snapshot' && e.event_id<=cursor)continue
 // Refresh authoritative state on every event, including replay snapshots.
 await snapshot(e.task_id)
 if(abort.signal.aborted)return
 setEvents(old=>mergeEvents(old,e));const approval=e.safe_payload.approval_id ?? e.safe_payload.approval_ref
 if(typeof approval==='string')setApprovals(old=>old.includes(approval)?old:[...old,approval])
 cursor=Math.max(cursor,e.event_id)
 }
 }
 }catch(e){if(e instanceof ApiError && e.status===409){cursor=0;setEvents([])}if(!abort.signal.aborted)setError(e instanceof Error?e.message:'Event connection lost')}
 finally{await reader?.cancel().catch(()=>{});reader?.releaseLock();reader=undefined;if(!abort.signal.aborted)retry=setTimeout(()=>void connect(),1500)} }
 void connect();return()=>{abort.abort();clearTimeout(retry)} },[])
 const active=Object.values(tasks).some(t=>['queued','prepared','running'].includes(t.status))
 return <section className="task-workspace" aria-label="Task workspace"><EmergencyStop onStop={()=>{setStopped(true);onRefresh()}}/><CommandInput disabled={stopped||health.stopped||active} onTask={id=>{void apiRequest('GET /api/tasks/{task_id}',{path:{task_id:id}}).then(task=>setTasks(old=>({...old,[id]:task}))).catch(e=>setError(e.message))}}/>{error&&<p role="alert">{error} · Reconnecting to task history…</p>}<VoicePanel stopped={stopped||health.stopped}/><HealthPanel health={health}/><MemoryPanel/><IntegrationPanel stopped={stopped||health.stopped}/><TaskTimeline events={events}/>{Object.values(tasks).map(task=><TaskResult key={task.task_id} task={task}/>)}{approvals.map(id=><ApprovalPanel key={id} id={id}/>)}</section>
}
