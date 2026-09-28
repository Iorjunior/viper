/**
 * Fetch-based typed HTTP client with error handling.
 */

export class ApiError extends Error {
  status: number
  statusText: string
  data: unknown

  constructor(status: number, statusText: string, data: unknown) {
    super(`API Error ${status}: ${statusText}`)
    this.name = 'ApiError'
    this.status = status
    this.statusText = statusText
    this.data = data
  }
}

export async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const headers = new Headers(options.headers || {})
  if (
    !headers.has('Content-Type') &&
    options.body &&
    typeof options.body === 'string'
  ) {
    headers.set('Content-Type', 'application/json')
  }

  const response = await fetch(path, {
    ...options,
    headers,
  })

  if (!response.ok) {
    let errorData: unknown
    try {
      errorData = await response.json()
    } catch {
      errorData = await response.text()
    }
    throw new ApiError(response.status, response.statusText, errorData)
  }

  if (response.status === 204) {
    return {} as T
  }

  return response.json() as Promise<T>
}
