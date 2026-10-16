// Generated from the current backend OpenAPI schema. Do not edit.
import type * as Types from './types.gen'

export interface ApiOperations {
  "GET /api/events": { request: Types.StreamEventsApiEventsGetData; response: Types.StreamEventsApiEventsGetResponses[keyof Types.StreamEventsApiEventsGetResponses] }
  "GET /api/tasks/{task_id}/events": { request: Types.StreamTaskEventsApiTasksTaskIdEventsGetData; response: Types.StreamTaskEventsApiTasksTaskIdEventsGetResponses[keyof Types.StreamTaskEventsApiTasksTaskIdEventsGetResponses] }
  "GET /api/approvals/{approval_id}": { request: Types.GetApprovalApiApprovalsApprovalIdGetData; response: Types.GetApprovalApiApprovalsApprovalIdGetResponses[keyof Types.GetApprovalApiApprovalsApprovalIdGetResponses] }
  "GET /api/approvals/{approval_id}/preview": { request: Types.GetPreviewApiApprovalsApprovalIdPreviewGetData; response: Types.GetPreviewApiApprovalsApprovalIdPreviewGetResponses[keyof Types.GetPreviewApiApprovalsApprovalIdPreviewGetResponses] }
  "POST /api/approvals/{approval_id}/resolve": { request: Types.ResolveApiApprovalsApprovalIdResolvePostData; response: Types.ResolveApiApprovalsApprovalIdResolvePostResponses[keyof Types.ResolveApiApprovalsApprovalIdResolvePostResponses] }
  "GET /api/session": { request: Types.SessionStatusApiSessionGetData; response: Types.SessionStatusApiSessionGetResponses[keyof Types.SessionStatusApiSessionGetResponses] }
  "POST /api/session": { request: Types.CreateSessionApiSessionPostData; response: Types.CreateSessionApiSessionPostResponses[keyof Types.CreateSessionApiSessionPostResponses] }
  "DELETE /api/session": { request: Types.DeleteSessionApiSessionDeleteData; response: Types.DeleteSessionApiSessionDeleteResponses[keyof Types.DeleteSessionApiSessionDeleteResponses] }
  "GET /api/health": { request: Types.HealthApiHealthGetData; response: Types.HealthApiHealthGetResponses[keyof Types.HealthApiHealthGetResponses] }
  "POST /api/tasks": { request: Types.CreateTaskApiTasksPostData; response: Types.CreateTaskApiTasksPostResponses[keyof Types.CreateTaskApiTasksPostResponses] }
  "GET /api/tasks/{task_id}": { request: Types.GetTaskApiTasksTaskIdGetData; response: Types.GetTaskApiTasksTaskIdGetResponses[keyof Types.GetTaskApiTasksTaskIdGetResponses] }
  "POST /api/stop": { request: Types.StopApiStopPostData; response: Types.StopApiStopPostResponses[keyof Types.StopApiStopPostResponses] }
}
