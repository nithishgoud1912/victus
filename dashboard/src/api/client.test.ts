import { afterEach, beforeEach, describe, expect, expectTypeOf, it, vi } from 'vitest'
import { ApiError, apiRequest, clearSessionToken, setSessionToken } from './client'
import type { HealthResponse } from './generated/types.gen'

const credential = 'fixture-token-' + 'x'.repeat(32)
const fetchMock = vi.fn<typeof fetch>()
const ok = () => new Response(JSON.stringify({ status: 'ok', mode: 'foundation', stopped: false, emergency_hotkey: 'disabled', tools: [] }), { headers: { 'Content-Type': 'application/json' } })

beforeEach(() => {
  clearSessionToken()
  vi.stubEnv('DEV', true)
  vi.stubGlobal('fetch', fetchMock)
  fetchMock.mockReset()
})
afterEach(() => { vi.unstubAllGlobals(); vi.unstubAllEnvs() })

describe('authenticated transport', () => {
  it('uses one request ID for tracing and deduplication, with a memory bearer', async () => {
    setSessionToken(credential)
    fetchMock.mockResolvedValue(ok())
    const health = await apiRequest('GET /api/health', { requestId: 'fixture-request-1' })
    expectTypeOf(health).toEqualTypeOf<HealthResponse>()
    const [url, options] = fetchMock.mock.calls[0]
    expect(String(url)).toBe('http://127.0.0.1:8765/api/health')
    const headers = new Headers(options?.headers)
    expect(headers.get('Authorization')).toBe(`Bearer ${credential}`)
    expect(headers.get('X-Request-ID')).toBe('fixture-request-1')
    expect(headers.get('X-Client-Request-ID')).toBe('fixture-request-1')
    expect(options?.credentials).toBe('omit')
    expect(options?.redirect).toBe('error')
  })

  it('generates IDs and serializes a typed mutation without retries', async () => {
    fetchMock.mockResolvedValue(new Response('{"task_id":"id","status":"queued"}', { status: 202, headers: { 'Content-Type': 'application/json' } }))
    await apiRequest('POST /api/tasks', { body: { tool: 'fs.create_note', arguments: { filename: 'note.txt', text: 'fixture' } } })
    const options = fetchMock.mock.calls[0][1]
    expect(new Headers(options?.headers).get('X-Request-ID')).toMatch(/^[0-9a-f-]{36}$/)
    expect(JSON.parse(String(options?.body)).arguments.filename).toBe('note.txt')
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('encodes path values and never sends credentials to another host', async () => {
    fetchMock.mockResolvedValue(ok())
    await apiRequest('GET /api/tasks/{task_id}', { path: { task_id: 'evil/../../?url=https://other.test' } })
    const url = new URL(String(fetchMock.mock.calls[0][0]))
    expect(url.origin).toBe('http://127.0.0.1:8765')
    expect(url.pathname).toContain('%2F')
  })

  it('supports authenticated cursor streaming through the same boundary', async () => {
    const response = new Response('data: fixture\n\n', { headers: { 'Content-Type': 'text/event-stream' } })
    fetchMock.mockResolvedValue(response)
    const controller = new AbortController()
    const stream = await apiRequest('GET /api/events', { response: 'stream', query: { cursor: 42 }, signal: controller.signal })
    expect(stream).toBe(response)
    expect(String(fetchMock.mock.calls[0][0])).toContain('cursor=42')
    expect(fetchMock.mock.calls[0][1]?.signal).toBe(controller.signal)
  })

  it('uses same-origin cookies in production after the bootstrap token is cleared', async () => {
    vi.stubEnv('DEV', false)
    vi.stubGlobal('window', { location: { origin: 'http://127.0.0.1:8765' } })
    setSessionToken(credential)
    clearSessionToken()
    fetchMock.mockResolvedValue(ok())
    await apiRequest('GET /api/health')
    expect(fetchMock.mock.calls[0][1]?.credentials).toBe('same-origin')
    expect(new Headers(fetchMock.mock.calls[0][1]?.headers).has('Authorization')).toBe(false)
  })

  it('forgets a rejected bearer and requires explicit reconnection', async () => {
    setSessionToken(credential)
    fetchMock.mockResolvedValueOnce(new Response('{}', { status: 401 })).mockResolvedValueOnce(ok())
    await expect(apiRequest('POST /api/stop')).rejects.toMatchObject({ status: 401, code: 'HTTP_401' })
    await apiRequest('GET /api/health')
    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(new Headers(fetchMock.mock.calls[1][1]?.headers).has('Authorization')).toBe(false)
  })

  it('never sends a production token to an unexpected origin or port', async () => {
    vi.stubEnv('DEV', false)
    vi.stubGlobal('window', { location: { origin: 'https://untrusted.test' } })
    setSessionToken(credential)
    await expect(apiRequest('POST /api/session')).rejects.toMatchObject({ code: 'UNTRUSTED_ORIGIN' })
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('does not let a late rejection erase a newer session', async () => {
    let resolve!: (response: Response) => void
    fetchMock.mockReturnValueOnce(new Promise<Response>((done) => { resolve = done }))
    setSessionToken(credential)
    const stale = apiRequest('GET /api/health')
    const fresh = 'fresh-' + credential
    setSessionToken(fresh)
    resolve(new Response('{}', { status: 401 }))
    await expect(stale).rejects.toBeInstanceOf(ApiError)
    fetchMock.mockResolvedValueOnce(ok())
    await apiRequest('GET /api/health')
    expect(new Headers(fetchMock.mock.calls[1][1]?.headers).get('Authorization')).toBe(`Bearer ${fresh}`)
  })

  it.each([403, 404, 409, 422, 429, 500])('normalizes HTTP %s without exposing raw inputs', async (status) => {
    fetchMock.mockResolvedValue(new Response('{"detail":{"input":"PRIVATE_INPUT"}}', { status, headers: { 'X-Request-ID': 'server-reference' } }))
    try { await apiRequest('POST /api/stop'); expect.fail('Request should fail') }
    catch (error) {
      expect(error).toBeInstanceOf(ApiError)
      expect(error).toMatchObject({ status, requestId: 'server-reference' })
      expect(JSON.stringify(error)).not.toContain('PRIVATE_INPUT')
    }
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('normalizes network failures and cancelled calls', async () => {
    fetchMock.mockRejectedValue(new Error('PRIVATE_REQUEST_DATA'))
    await expect(apiRequest('GET /api/health')).rejects.toMatchObject({ code: 'NETWORK_ERROR', status: 0 })
    const controller = new AbortController()
    controller.abort()
    await expect(apiRequest('GET /api/health', { signal: controller.signal })).rejects.toMatchObject({ code: 'ABORTED' })
  })

  it('handles 204 and rejects malformed success responses', async () => {
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }))
    await expect(apiRequest('DELETE /api/session')).resolves.toBeUndefined()
    fetchMock.mockResolvedValueOnce(new Response('html'))
    await expect(apiRequest('GET /api/health')).rejects.toMatchObject({ code: 'INVALID_RESPONSE' })
    fetchMock.mockResolvedValueOnce(new Response('{', { headers: { 'Content-Type': 'application/json' } }))
    await expect(apiRequest('GET /api/health')).rejects.toMatchObject({ code: 'INVALID_RESPONSE' })
  })
})

// Checked by the generated template's TypeScript build; never executed.
export function compileTimeContractChecks() {
  // @ts-expect-error API body comes from the exported backend model.
  void apiRequest('POST /api/tasks', { body: { tool: 'unknown.tool' } })
  // @ts-expect-error A task lookup requires a path parameter.
  void apiRequest('GET /api/tasks/{task_id}')
  // @ts-expect-error Tokens cannot be supplied through query options.
  void apiRequest('GET /api/health', { query: { token: credential } })
}
