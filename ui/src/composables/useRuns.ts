import { ref, getCurrentInstance, onUnmounted } from 'vue'
import { fetchRuns, fetchRun } from '../api/runs'
import type {
  Run,
  RunDetailResponse,
  StageRun,
  WsStageEvent,
} from '../api/types'

export function useRuns() {
  const runs = ref<Run[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  const currentRun = ref<RunDetailResponse | null>(null)
  const isLoadingDetail = ref(false)
  const detailError = ref<string | null>(null)

  let pollIntervalId: ReturnType<typeof setInterval> | null = null

  async function loadRuns(limit = 50, offset = 0) {
    isLoading.value = true
    error.value = null
    try {
      runs.value = await fetchRuns(limit, offset)
    } catch (err: unknown) {
      error.value = err instanceof Error ? err.message : 'Failed to load runs'
    } finally {
      isLoading.value = false
    }
  }

  async function loadRunDetail(
    id: string,
    isSilent = false
  ): Promise<RunDetailResponse | null> {
    if (!isSilent) {
      isLoadingDetail.value = true
      detailError.value = null
    }
    try {
      const data = await fetchRun(id)
      currentRun.value = data
      return data
    } catch (err: unknown) {
      if (!isSilent) {
        detailError.value =
          err instanceof Error ? err.message : `Failed to load run ${id}`
      }
      return null
    } finally {
      if (!isSilent) {
        isLoadingDetail.value = false
      }
    }
  }

  function startPolling(id: string, intervalMs = 1500) {
    stopPolling()
    pollIntervalId = setInterval(async () => {
      const run = await loadRunDetail(id, true)
      if (run && run.status !== 'pending' && run.status !== 'running') {
        stopPolling()
      }
    }, intervalMs)
  }

  function stopPolling() {
    if (pollIntervalId) {
      clearInterval(pollIntervalId)
      pollIntervalId = null
    }
  }

  function applyWsEvent(event: WsStageEvent) {
    if (!currentRun.value || currentRun.value.id !== event.run_id) {
      return
    }

    if (event.event === 'run_started') {
      currentRun.value.status = 'running'
    } else if (event.event === 'stage_started' && event.stage_id) {
      currentRun.value.status = 'running'
      const existing = currentRun.value.stage_runs.find(
        (s) => s.stage_id === event.stage_id
      )
      if (existing) {
        existing.status = 'running'
        existing.started_at = new Date().toISOString()
      } else {
        const newStage: StageRun = {
          id: `stage-${event.stage_id}`,
          run_id: event.run_id,
          stage_id: event.stage_id,
          status: 'running',
          output: '{}',
          error: null,
          started_at: new Date().toISOString(),
          finished_at: null,
        }
        currentRun.value.stage_runs.push(newStage)
      }
    } else if (event.event === 'stage_completed' && event.stage_id) {
      const existing = currentRun.value.stage_runs.find(
        (s) => s.stage_id === event.stage_id
      )
      if (existing) {
        existing.status = 'completed'
        existing.output = JSON.stringify(event.output || {})
        existing.finished_at = new Date().toISOString()
      }
    } else if (event.event === 'stage_failed' && event.stage_id) {
      const existing = currentRun.value.stage_runs.find(
        (s) => s.stage_id === event.stage_id
      )
      if (existing) {
        existing.status = 'failed'
        existing.error = event.error || 'Stage execution failed'
        existing.finished_at = new Date().toISOString()
      }
    } else if (event.event === 'run_completed') {
      currentRun.value.status = 'completed'
      currentRun.value.finished_at = new Date().toISOString()
      const rawOutputs = event.outputs ?? event.stage_results
      if (rawOutputs) {
        currentRun.value.outputs =
          typeof rawOutputs === 'string'
            ? rawOutputs
            : JSON.stringify(rawOutputs)
      }
      stopPolling()
    } else if (event.event === 'run_failed') {
      currentRun.value.status = 'failed'
      currentRun.value.finished_at = new Date().toISOString()
      stopPolling()
    }
  }

  if (getCurrentInstance()) {
    onUnmounted(() => {
      stopPolling()
    })
  }

  return {
    runs,
    isLoading,
    error,
    currentRun,
    isLoadingDetail,
    detailError,
    loadRuns,
    loadRunDetail,
    startPolling,
    stopPolling,
    applyWsEvent,
  }
}
