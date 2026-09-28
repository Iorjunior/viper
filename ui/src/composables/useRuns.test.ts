import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useRuns } from './useRuns'
import * as runsApi from '../api/runs'
import type { Run, RunDetailResponse } from '../api/types'

const mockRunDetail: RunDetailResponse = {
  id: 'run-123',
  pipeline_id: 'full_dubbing',
  status: 'pending',
  inputs: '{"source":"video.mp4"}',
  outputs: '{}',
  created_at: '2026-09-25T12:00:00Z',
  finished_at: null,
  stage_runs: [],
}

describe('useRuns', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('loads runs list', async () => {
    const mockRuns: Run[] = [
      {
        id: 'run-1',
        pipeline_id: 'dubbing',
        status: 'completed',
        inputs: '{}',
        outputs: '{}',
        created_at: '2026-09-25T12:00:00Z',
        finished_at: '2026-09-25T12:01:00Z',
      },
    ]
    vi.spyOn(runsApi, 'fetchRuns').mockResolvedValue(mockRuns)
    const { loadRuns, runs } = useRuns()

    await loadRuns()
    expect(runs.value.length).toBe(1)
    expect(runs.value[0].id).toBe('run-1')
  })

  it('applies WebSocket stage events reactively', async () => {
    vi.spyOn(runsApi, 'fetchRun').mockResolvedValue(
      JSON.parse(JSON.stringify(mockRunDetail))
    )
    const { loadRunDetail, currentRun, applyWsEvent } = useRuns()

    await loadRunDetail('run-123')
    expect(currentRun.value?.status).toBe('pending')

    // Run started event
    applyWsEvent({
      event: 'run_started',
      run_id: 'run-123',
    })
    expect(currentRun.value?.status).toBe('running')

    // Stage started event
    applyWsEvent({
      event: 'stage_started',
      run_id: 'run-123',
      stage_id: 'extract_audio',
    })

    expect(currentRun.value?.status).toBe('running')
    expect(currentRun.value?.stage_runs.length).toBe(1)
    expect(currentRun.value?.stage_runs[0].status).toBe('running')

    // Stage completed event
    applyWsEvent({
      event: 'stage_completed',
      run_id: 'run-123',
      stage_id: 'extract_audio',
      output: { audio: 'extracted.wav' },
    })

    expect(currentRun.value?.stage_runs[0].status).toBe('completed')
    expect(currentRun.value?.stage_runs[0].output).toContain('extracted.wav')

    // Run completed event with outputs
    applyWsEvent({
      event: 'run_completed',
      run_id: 'run-123',
      outputs: { final: 'video_dubbed.mp4' },
    })

    expect(currentRun.value?.status).toBe('completed')
    expect(currentRun.value?.outputs).toContain('video_dubbed.mp4')
  })

  it('polls run detail until finished', async () => {
    vi.useFakeTimers()
    const mockPending = { ...mockRunDetail, status: 'pending' }
    const mockCompleted = { ...mockRunDetail, status: 'completed' }

    const fetchSpy = vi
      .spyOn(runsApi, 'fetchRun')
      .mockResolvedValueOnce(mockPending)
      .mockResolvedValueOnce(mockCompleted)

    const { startPolling, currentRun } = useRuns()

    startPolling('run-123', 1000)

    await vi.advanceTimersByTimeAsync(1000)
    expect(fetchSpy).toHaveBeenCalledTimes(1)
    expect(currentRun.value?.status).toBe('pending')

    await vi.advanceTimersByTimeAsync(1000)
    expect(fetchSpy).toHaveBeenCalledTimes(2)
    expect(currentRun.value?.status).toBe('completed')

    // Should stop polling once completed
    await vi.advanceTimersByTimeAsync(2000)
    expect(fetchSpy).toHaveBeenCalledTimes(2)

    vi.useRealTimers()
  })
})
