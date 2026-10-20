import type { TaskResult as Result } from '../../api/generated/types.gen'

export function TaskResult({ task }: { task: Result }) {
  const verified = task.status === 'succeeded' && task.verified
  return <section className="service-card" aria-label="Task result">
    <h2>{verified ? 'Verified output' : task.status === 'waiting_for_review' ? 'Waiting for Save approval' : 'Task: ' + task.status}</h2>
    <p>Task {task.task_id}</p>
    {task.output_name && <p>Output: {task.output_name}</p>}
    {task.sha256 && <p>SHA-256: {task.sha256}</p>}
    {!verified && <p>Verification is incomplete. No verified output is confirmed.</p>}
    {task.status === 'unknown' && <p role="status">This action may already have changed the file or application. Inspect the destination and application without repeating the action. Refreshing task history only reads saved status; it does not retry the action.</p>}
    {task.error_code && <p>Error: {task.error_code}</p>}
  </section>
}
