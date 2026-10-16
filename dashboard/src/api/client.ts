import type { ApiOperations } from './generated/operations.gen'

type ApiOperation = keyof ApiOperations
type Options<K extends ApiOperation> = Omit<ApiOperations[K]['request'], 'url' | 'headers'> & {
  requestId?: string
  signal?: AbortSignal
}
type TransportOptions = {
  body?: unknown
  path?: Record<string, string | number>
  query?: Record<string, string | number | boolean | null | undefined>
  requestId?: string
  signal?: AbortSignal
  response?: 'json' | 'stream'
}

let token: string | null = null
let authEpoch = 0

export function clearSessionToken() {
  token = null
  authEpoch += 1
}

export function setSessionToken(value: string) {
  const candidate = value.trim()
  if (candidate.length < 32 || candidate.length > 512 || /[\r\n]/.test(candidate)) {
    throw new Error('Enter the session token from your local VICTUS service.')
  }
  token = candidate
  authEpoch += 1
}

export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly requestId: string

  constructor(message: string, status: number, code: string, requestId: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.requestId = requestId
  }
}

const messages: Record<number, string> = {
  401: 'Your session ended or the token was not accepted. Connect again.',
  403: 'This connection is not allowed. Use the configured local dashboard address.',
  404: 'The requested item could not be found.',
  409: 'This request conflicts with its current state. Refresh before continuing.',
  422: 'The request was not accepted. Check the entered values.',
  429: 'The service is busy. Wait a moment before trying again.',
}

// This is the sole browser HTTP boundary. No transparent retries of mutations.
export function apiRequest<K extends ApiOperation>(operation: K, options: Options<K> & { response: 'stream' }): Promise<Response>
export function apiRequest<K extends ApiOperation>(operation: K, ...options: {} extends Options<K> ? [options?: Options<K>] : [options: Options<K>]): Promise<ApiOperations[K]['response']>
export async function apiRequest(operation: ApiOperation, options: TransportOptions = {}): Promise<unknown> {
  const requestId = options.requestId ?? crypto.randomUUID()
  if (!/^[A-Za-z0-9_-]{1,128}$/.test(requestId)) throw new Error('Invalid request identifier.')
  const [method, template] = operation.split(' ')
  if (!template?.startsWith('/api/')) throw new Error('Unsupported API route.')
  const path = template.replace(/\{([^}]+)\}/g, (_, key: string) => {
    const value = options.path?.[key]
    if (value === undefined) throw new Error('Missing API path parameter.')
    return encodeURIComponent(String(value))
  })
  const base = import.meta.env.DEV ? 'http://127.0.0.1:8765' : window.location.origin
  if (!import.meta.env.DEV && !['http://127.0.0.1:8765', 'http://localhost:8765'].includes(base)) {
    throw new ApiError('Open this dashboard from your local VICTUS service on port 8765.', 0, 'UNTRUSTED_ORIGIN', requestId)
  }
  const url = new URL(path, base)
  for (const [key, value] of Object.entries(options.query ?? {})) {
    if (value !== undefined && value !== null) url.searchParams.set(key, String(value))
  }
  const epoch = authEpoch
  const headers = new Headers({
    Accept: options.response === 'stream' ? 'text/event-stream' : 'application/json',
    'X-Request-ID': requestId,
    'X-Client-Request-ID': requestId,
  })
  if (token !== null) headers.set('Authorization', `Bearer ${token}`)
  if (options.body !== undefined) headers.set('Content-Type', 'application/json')
  const controller = new AbortController()
  const abort = () => controller.abort()
  const timer = options.response === 'stream' ? undefined : setTimeout(abort, 15_000)
  options.signal?.addEventListener('abort', abort, { once: true })
  if (options.signal?.aborted) controller.abort()
  try {
    const response = await fetch(url, {
      method, headers,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      signal: options.response === 'stream' ? options.signal : controller.signal,
      credentials: import.meta.env.DEV ? 'omit' : 'same-origin',
      redirect: 'error', cache: 'no-store',
    })
    const correlation = response.headers.get('X-Request-ID') ?? requestId
    if (!response.ok) {
      if (response.status === 401 && epoch === authEpoch) clearSessionToken()
      // Do not surface validation inputs, raw server bodies, credentials or URLs.
      throw new ApiError(messages[response.status] ?? 'The local service could not complete this request.',
        response.status, `HTTP_${response.status}`, correlation)
    }
    if (options.response === 'stream') return response
    if (response.status === 204) return undefined
    if (!response.headers.get('Content-Type')?.includes('application/json')) {
      throw new ApiError('The local service returned an unexpected response.', response.status, 'INVALID_RESPONSE', correlation)
    }
    try {
      return await response.json()
    } catch {
      throw new ApiError('The local service returned an unreadable response.', response.status, 'INVALID_RESPONSE', correlation)
    }
  } catch (error) {
    if (error instanceof ApiError) throw error
    if (options.signal?.aborted || controller.signal.aborted) {
      throw new ApiError('The request was cancelled or timed out.', 0, 'ABORTED', requestId)
    }
    throw new ApiError('Cannot reach your local VICTUS service. Check that it is running.', 0, 'NETWORK_ERROR', requestId)
  } finally {
    if (timer !== undefined) clearTimeout(timer)
    options.signal?.removeEventListener('abort', abort)
  }
}
