import { describe, it, expect, vi, beforeEach } from 'vitest'
import { usePipelines } from './usePipelines'
import * as pipelinesApi from '../api/pipelines'
import type { PipelineManifest } from '../api/types'

const mockPipelines: PipelineManifest[] = [
  {
    id: 'dubbing',
    name: 'Full Dubbing',
    description: 'Video translation and dubbing',
    stages: [],
    inputs: [],
    outputs: {},
    builtin: true,
    icon: 'mic',
    tags: ['video', 'speech'],
  },
  {
    id: 'transcribe',
    name: 'Audio Transcriber',
    description: 'Speech to text transcription',
    stages: [],
    inputs: [],
    outputs: {},
    builtin: true,
    icon: 'file-text',
    tags: ['audio', 'speech'],
  },
]

describe('usePipelines', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('loads pipelines and extracts unique tags', async () => {
    vi.spyOn(pipelinesApi, 'fetchPipelines').mockResolvedValue(mockPipelines)
    const { loadPipelines, pipelines, allTags } = usePipelines()

    await loadPipelines(true)
    expect(pipelines.value.length).toBe(2)
    expect(allTags.value).toEqual(['audio', 'speech', 'video'])
  })

  it('filters pipelines by tag and search query', async () => {
    vi.spyOn(pipelinesApi, 'fetchPipelines').mockResolvedValue(mockPipelines)
    const {
      loadPipelines,
      searchQuery,
      selectedTag,
      filteredPipelines,
      getPipelineById,
    } = usePipelines()

    await loadPipelines(true)

    // Filter by tag
    selectedTag.value = 'audio'
    expect(filteredPipelines.value.length).toBe(1)
    expect(filteredPipelines.value[0].id).toBe('transcribe')

    // Filter by search query
    selectedTag.value = null
    searchQuery.value = 'dubbing'
    expect(filteredPipelines.value.length).toBe(1)
    expect(filteredPipelines.value[0].id).toBe('dubbing')

    // Helper lookup
    expect(getPipelineById('transcribe')?.name).toBe('Audio Transcriber')
  })
})
