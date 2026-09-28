/**
 * Pipeline API operations.
 */

import { request } from './client'
import type { PipelineManifest, Run } from './types'

export async function fetchPipelines(): Promise<PipelineManifest[]> {
  return request<PipelineManifest[]>('/api/pipelines')
}

export async function fetchPipeline(id: string): Promise<PipelineManifest> {
  return request<PipelineManifest>(`/api/pipelines/${encodeURIComponent(id)}`)
}

export async function triggerRun(
  pipelineId: string,
  inputs: Record<string, unknown>
): Promise<Run> {
  return request<Run>(`/api/pipelines/${encodeURIComponent(pipelineId)}/run`, {
    method: 'POST',
    body: JSON.stringify(inputs),
  })
}
