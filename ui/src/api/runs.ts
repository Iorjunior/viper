/**
 * Run and execution history API operations.
 */

import { request } from './client'
import type { Run, RunDetailResponse } from './types'

export async function fetchRuns(limit = 50, offset = 0): Promise<Run[]> {
  const params = new URLSearchParams({
    limit: limit.toString(),
    offset: offset.toString(),
  })
  return request<Run[]>(`/api/runs?${params.toString()}`)
}

export async function fetchRun(id: string): Promise<RunDetailResponse> {
  return request<RunDetailResponse>(`/api/runs/${encodeURIComponent(id)}`)
}

export function getAssetUrl(assetPath: string): string {
  // Strip leading slash if present
  const cleaned = assetPath.replace(/^\/+/, '')
  return `/api/assets/${cleaned}`
}
