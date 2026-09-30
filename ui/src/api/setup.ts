/**
 * Setup and system configuration API client operations.
 */

import { request } from './client'
import type {
  CompleteSetupRequest,
  SetupStatus,
  ValidateConnectionRequest,
  ValidateConnectionResponse,
} from './types'

export async function fetchSetupStatus(): Promise<SetupStatus> {
  return request<SetupStatus>('/api/setup/status')
}

export async function validateConnection(
  payload: ValidateConnectionRequest
): Promise<ValidateConnectionResponse> {
  return request<ValidateConnectionResponse>('/api/setup/validate-connection', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function downloadModel(
  modelId: string
): Promise<{ success: boolean; model_id: string; message: string }> {
  return request<{ success: boolean; model_id: string; message: string }>(
    '/api/setup/download-model',
    {
      method: 'POST',
      body: JSON.stringify({ model_id: modelId }),
    }
  )
}

export async function completeSetup(
  payload: CompleteSetupRequest
): Promise<{ success: boolean; message: string }> {
  return request<{ success: boolean; message: string }>('/api/setup/complete', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}
