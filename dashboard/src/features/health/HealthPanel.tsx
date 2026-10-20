import type { HealthResponse, WorkflowCapabilities } from '../../api/generated/types.gen'

export function HealthPanel({ health, capabilities, capabilityError }: {
  health: HealthResponse; capabilities: WorkflowCapabilities | null; capabilityError: string
}) {
  const stopped = health.stopped || capabilities?.stopped
  const resourceMessages: Record<string, string> = {
    LOCAL_RESOURCE_PRESSURE: 'Temporarily blocked by low available memory',
    LOCAL_RESOURCE_TELEMETRY_UNAVAILABLE: 'Current resource telemetry is unavailable',
    LOCAL_DISK_PRESSURE: 'Temporarily blocked by low workspace disk space',
    LOCAL_DISK_UNAVAILABLE: 'Workspace disk availability could not be checked',
  }
  const pressure = capabilities?.resource_blocked
    ? resourceMessages[capabilities.resource_reason ?? ''] ?? 'Temporarily blocked by local resource pressure'
    : ''
  function workflow(enabled: boolean | undefined, reason: string | null | undefined) {
    if (capabilityError) return capabilityError
    if (!capabilities) return 'Checking availability'
    if (!enabled) return reason || 'Qualification is required'
    if (stopped) return 'Qualified; service stopped. Restart before new work.'
    if (pressure) return `Qualified; ${pressure}`
    return 'Qualified and enabled'
  }
  const command = capabilities?.commands
  return <section className="service-card" aria-label="Dependency readiness">
    <h2>Dependency readiness</h2>
    <dl>
      <div><dt>Service</dt><dd>{stopped ? 'Stopped' : health.status}</dd></div>
      <div><dt>Mode</dt><dd>{health.mode}</dd></div>
      <div><dt>Local resources</dt><dd>{capabilityError || (!capabilities ? 'Checking availability' : pressure || 'Current memory and workspace disk checks passed')}</dd></div>
      <div><dt>Notepad checklist</dt><dd>{workflow(capabilities?.notepad_checklist?.enabled, capabilities?.notepad_checklist?.reason)}</dd></div>
      <div><dt>Browser research</dt><dd>{workflow(capabilities?.browser_research?.enabled, capabilities?.browser_research?.reason)} Bundled sources only; public websites are unavailable.</dd></div>
      <div><dt>Local reasoning model</dt><dd>{capabilityError || (!capabilities ? 'Checking availability' : !command?.reasoning_ready ? command?.reason || 'An exact installed local model is required' : `Pinned local model available: ${command.model_name}. Inference quality is not qualified by this readiness check.`)}</dd></div>
      <div><dt>Microphone</dt><dd>Use the voice panel to inspect capture availability. Recording requires an explicit start.</dd></div>
    </dl>
    <p>Available tools: {health.tools.join(', ') || 'None'}</p>
  </section>
}
