/**
 * Stage discovery and reflection API operations.
 */

import { request } from './client'
import type { StageDefinition } from './types'

export async function fetchStages(): Promise<StageDefinition[]> {
  return request<StageDefinition[]>('/api/stages')
}
