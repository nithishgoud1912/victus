// Generated from the current backend OpenAPI schema. Do not edit.
import type * as Types from './types.gen'

export interface ApiOperations {
  "GET /api/memory": { request: Types.RecallApiMemoryGetData; response: Types.RecallApiMemoryGetResponses[keyof Types.RecallApiMemoryGetResponses] }
  "POST /api/memory": { request: Types.RememberApiMemoryPostData; response: Types.RememberApiMemoryPostResponses[keyof Types.RememberApiMemoryPostResponses] }
  "GET /api/memory/export": { request: Types.ExportMemoryApiMemoryExportGetData; response: Types.ExportMemoryApiMemoryExportGetResponses[keyof Types.ExportMemoryApiMemoryExportGetResponses] }
  "POST /api/memory/{memory_id}": { request: Types.EditApiMemoryMemoryIdPostData; response: Types.EditApiMemoryMemoryIdPostResponses[keyof Types.EditApiMemoryMemoryIdPostResponses] }
  "DELETE /api/memory/{memory_id}": { request: Types.ForgetApiMemoryMemoryIdDeleteData; response: Types.ForgetApiMemoryMemoryIdDeleteResponses[keyof Types.ForgetApiMemoryMemoryIdDeleteResponses] }
  "POST /api/retention/cleanup": { request: Types.CleanupApiRetentionCleanupPostData; response: Types.CleanupApiRetentionCleanupPostResponses[keyof Types.CleanupApiRetentionCleanupPostResponses] }
  "GET /api/resources": { request: Types.ResourcesStatusApiResourcesGetData; response: Types.ResourcesStatusApiResourcesGetResponses[keyof Types.ResourcesStatusApiResourcesGetResponses] }
  "GET /api/diagnostics/preview": { request: Types.PreviewApiDiagnosticsPreviewGetData; response: Types.PreviewApiDiagnosticsPreviewGetResponses[keyof Types.PreviewApiDiagnosticsPreviewGetResponses] }
  "POST /api/diagnostics/export": { request: Types.DiagnosticExportApiDiagnosticsExportPostData; response: Types.DiagnosticExportApiDiagnosticsExportPostResponses[keyof Types.DiagnosticExportApiDiagnosticsExportPostResponses] }
  "GET /api/integrations": { request: Types.StatusApiIntegrationsGetData; response: Types.StatusApiIntegrationsGetResponses[keyof Types.StatusApiIntegrationsGetResponses] }
  "POST /api/integrations/cloud/preview": { request: Types.PreviewApiIntegrationsCloudPreviewPostData; response: Types.PreviewApiIntegrationsCloudPreviewPostResponses[keyof Types.PreviewApiIntegrationsCloudPreviewPostResponses] }
  "POST /api/integrations/cloud/review": { request: Types.ReviewApiIntegrationsCloudReviewPostData; response: Types.ReviewApiIntegrationsCloudReviewPostResponses[keyof Types.ReviewApiIntegrationsCloudReviewPostResponses] }
  "GET /api/voice": { request: Types.VoiceStatusApiVoiceGetData; response: Types.VoiceStatusApiVoiceGetResponses[keyof Types.VoiceStatusApiVoiceGetResponses] }
  "POST /api/voice/start": { request: Types.VoiceStartApiVoiceStartPostData; response: Types.VoiceStartApiVoiceStartPostResponses[keyof Types.VoiceStartApiVoiceStartPostResponses] }
  "POST /api/voice/wake/enable": { request: Types.WakeEnableApiVoiceWakeEnablePostData; response: Types.WakeEnableApiVoiceWakeEnablePostResponses[keyof Types.WakeEnableApiVoiceWakeEnablePostResponses] }
  "POST /api/voice/wake/disable": { request: Types.WakeDisableApiVoiceWakeDisablePostData; response: Types.WakeDisableApiVoiceWakeDisablePostResponses[keyof Types.WakeDisableApiVoiceWakeDisablePostResponses] }
  "POST /api/voice/finish": { request: Types.VoiceFinishApiVoiceFinishPostData; response: Types.VoiceFinishApiVoiceFinishPostResponses[keyof Types.VoiceFinishApiVoiceFinishPostResponses] }
  "POST /api/voice/cancel": { request: Types.VoiceCancelApiVoiceCancelPostData; response: Types.VoiceCancelApiVoiceCancelPostResponses[keyof Types.VoiceCancelApiVoiceCancelPostResponses] }
  "POST /api/voice/submit": { request: Types.VoiceSubmitApiVoiceSubmitPostData; response: Types.VoiceSubmitApiVoiceSubmitPostResponses[keyof Types.VoiceSubmitApiVoiceSubmitPostResponses] }
  "POST /api/voice/clarify": { request: Types.VoiceClarifyApiVoiceClarifyPostData; response: Types.VoiceClarifyApiVoiceClarifyPostResponses[keyof Types.VoiceClarifyApiVoiceClarifyPostResponses] }
  "POST /api/voice/displayed": { request: Types.VoiceDisplayedApiVoiceDisplayedPostData; response: Types.VoiceDisplayedApiVoiceDisplayedPostResponses[keyof Types.VoiceDisplayedApiVoiceDisplayedPostResponses] }
  "POST /api/voice/mute": { request: Types.VoiceMuteApiVoiceMutePostData; response: Types.VoiceMuteApiVoiceMutePostResponses[keyof Types.VoiceMuteApiVoiceMutePostResponses] }
  "GET /api/events": { request: Types.StreamEventsApiEventsGetData; response: Types.StreamEventsApiEventsGetResponses[keyof Types.StreamEventsApiEventsGetResponses] }
  "GET /api/tasks/{task_id}/events": { request: Types.StreamTaskEventsApiTasksTaskIdEventsGetData; response: Types.StreamTaskEventsApiTasksTaskIdEventsGetResponses[keyof Types.StreamTaskEventsApiTasksTaskIdEventsGetResponses] }
  "GET /api/approvals/{approval_id}": { request: Types.GetApprovalApiApprovalsApprovalIdGetData; response: Types.GetApprovalApiApprovalsApprovalIdGetResponses[keyof Types.GetApprovalApiApprovalsApprovalIdGetResponses] }
  "GET /api/approvals/{approval_id}/preview": { request: Types.GetPreviewApiApprovalsApprovalIdPreviewGetData; response: Types.GetPreviewApiApprovalsApprovalIdPreviewGetResponses[keyof Types.GetPreviewApiApprovalsApprovalIdPreviewGetResponses] }
  "POST /api/approvals/{approval_id}/resolve": { request: Types.ResolveApiApprovalsApprovalIdResolvePostData; response: Types.ResolveApiApprovalsApprovalIdResolvePostResponses[keyof Types.ResolveApiApprovalsApprovalIdResolvePostResponses] }
  "GET /api/session": { request: Types.SessionStatusApiSessionGetData; response: Types.SessionStatusApiSessionGetResponses[keyof Types.SessionStatusApiSessionGetResponses] }
  "POST /api/session": { request: Types.CreateSessionApiSessionPostData; response: Types.CreateSessionApiSessionPostResponses[keyof Types.CreateSessionApiSessionPostResponses] }
  "DELETE /api/session": { request: Types.DeleteSessionApiSessionDeleteData; response: Types.DeleteSessionApiSessionDeleteResponses[keyof Types.DeleteSessionApiSessionDeleteResponses] }
  "GET /api/workflows/capabilities": { request: Types.CapabilitiesApiWorkflowsCapabilitiesGetData; response: Types.CapabilitiesApiWorkflowsCapabilitiesGetResponses[keyof Types.CapabilitiesApiWorkflowsCapabilitiesGetResponses] }
  "POST /api/workflows/browser-research": { request: Types.SubmitResearchApiWorkflowsBrowserResearchPostData; response: Types.SubmitResearchApiWorkflowsBrowserResearchPostResponses[keyof Types.SubmitResearchApiWorkflowsBrowserResearchPostResponses] }
  "POST /api/workflows/notepad-checklist": { request: Types.SubmitNotepadApiWorkflowsNotepadChecklistPostData; response: Types.SubmitNotepadApiWorkflowsNotepadChecklistPostResponses[keyof Types.SubmitNotepadApiWorkflowsNotepadChecklistPostResponses] }
  "POST /api/commands": { request: Types.SubmitApiCommandsPostData; response: Types.SubmitApiCommandsPostResponses[keyof Types.SubmitApiCommandsPostResponses] }
  "GET /api/commands/{command_id}": { request: Types.SnapshotApiCommandsCommandIdGetData; response: Types.SnapshotApiCommandsCommandIdGetResponses[keyof Types.SnapshotApiCommandsCommandIdGetResponses] }
  "POST /api/commands/{command_id}/clarify": { request: Types.ClarifyApiCommandsCommandIdClarifyPostData; response: Types.ClarifyApiCommandsCommandIdClarifyPostResponses[keyof Types.ClarifyApiCommandsCommandIdClarifyPostResponses] }
  "GET /api/health": { request: Types.HealthApiHealthGetData; response: Types.HealthApiHealthGetResponses[keyof Types.HealthApiHealthGetResponses] }
  "POST /api/tasks": { request: Types.CreateTaskApiTasksPostData; response: Types.CreateTaskApiTasksPostResponses[keyof Types.CreateTaskApiTasksPostResponses] }
  "GET /api/tasks/{task_id}": { request: Types.GetTaskApiTasksTaskIdGetData; response: Types.GetTaskApiTasksTaskIdGetResponses[keyof Types.GetTaskApiTasksTaskIdGetResponses] }
  "POST /api/stop": { request: Types.StopApiStopPostData; response: Types.StopApiStopPostResponses[keyof Types.StopApiStopPostResponses] }
}
