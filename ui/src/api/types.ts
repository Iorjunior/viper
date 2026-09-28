/**
 * API data models and type definitions for Viper frontend.
 */

export interface PipelineInput {
  name: string
  type: string
  label?: string | null
  required: boolean
  default?: unknown
  options?: string[]
}

export interface PipelineStageConfig {
  id: string
  stage: string
  inputs: Record<string, unknown>
  options?: Record<string, unknown>
}

export interface PipelineManifest {
  id: string
  name: string
  description: string
  stages: PipelineStageConfig[]
  inputs: PipelineInput[] | Record<string, unknown>
  outputs: Record<string, unknown>
  builtin: boolean
  icon: string
  tags: string[]
}

export interface Run {
  id: string
  pipeline_id: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  inputs: string // JSON string
  outputs: string // JSON string
  created_at: string
  finished_at: string | null
}

export interface StageRun {
  id: string
  run_id: string
  stage_id: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  output: string // JSON string
  error: string | null
  started_at: string | null
  finished_at: string | null
}

export interface RunDetailResponse {
  id: string
  pipeline_id: string
  status: string
  inputs: string
  outputs: string
  created_at: string
  finished_at: string | null
  stage_runs: StageRun[]
}

export interface StageDefinition {
  name: string
  description: string
  inputs: Record<string, unknown>
}

export interface WsStageEvent {
  event:
    | 'run_started'
    | 'stage_started'
    | 'stage_progress'
    | 'stage_completed'
    | 'stage_failed'
    | 'run_completed'
    | 'run_failed'
  run_id: string
  pipeline_id?: string
  stage_id?: string
  percent?: number
  output?: unknown
  outputs?: unknown
  error?: string
  status?: string
  stage_results?: Record<string, unknown>
}
