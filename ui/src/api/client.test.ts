import { describe, it, expect, vi, beforeEach } from 'vitest'
import { request, ApiError } from './client'

describe('ApiClient', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('performs successful GET request and returns JSON', async () => {
    const mockData = [{ id: 'test' }]
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => mockData,
    })

    const result = await request<typeof mockData>('/api/test')
    expect(result).toEqual(mockData)
    expect(fetch).toHaveBeenCalledWith(
      '/api/test',
      expect.objectContaining({
        headers: expect.any(Headers),
      })
    )
  })

  it('sets Content-Type to application/json when body string is provided', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ status: 'ok' }),
    })

    await request('/api/test', {
      method: 'POST',
      body: JSON.stringify({ key: 'val' }),
    })

    const calls = (fetch as ReturnType<typeof vi.fn>).mock.calls
    const headers = calls[0][1].headers as Headers
    expect(headers.get('Content-Type')).toBe('application/json')
  })

  it('throws ApiError on failed response with parsed error JSON', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      statusText: 'Not Found',
      json: async () => ({ detail: 'Resource not found' }),
    })

    await expect(request('/api/missing')).rejects.toThrow(ApiError)
  })

  it('returns empty object on 204 No Content', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 204,
      statusText: 'No Content',
    })

    const result = await request('/api/no-content')
    expect(result).toEqual({})
  })
})
