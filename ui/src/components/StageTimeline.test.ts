import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ui from '@nuxt/ui/vue-plugin'
import StageTimeline from './StageTimeline.vue'
import type { StageRun, PipelineStageConfig } from '../api/types'

describe('StageTimeline', () => {
  it('renders stages with appropriate status badges', () => {
    const stages: PipelineStageConfig[] = [
      { id: 'extract', stage: 'extract_audio', inputs: {} },
      { id: 'transcribe', stage: 'transcribe', inputs: {} },
    ]

    const stageRuns: StageRun[] = [
      {
        id: 'sr-1',
        run_id: 'run-1',
        stage_id: 'extract',
        status: 'completed',
        output: '{}',
        error: null,
        started_at: '2026-09-25T12:00:00Z',
        finished_at: '2026-09-25T12:00:05Z',
      },
    ]

    const wrapper = mount(StageTimeline, {
      props: {
        stages,
        stageRuns,
      },
      global: {
        plugins: [ui],
      },
    })

    expect(wrapper.text()).toContain('extract_audio')
    expect(wrapper.text()).toContain('transcribe')
    expect(wrapper.text()).toContain('completed')
    expect(wrapper.text()).toContain('pending')
  })
})
