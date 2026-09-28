import { ref, computed } from 'vue'
import { fetchPipelines } from '../api/pipelines'
import type { PipelineManifest } from '../api/types'

const pipelines = ref<PipelineManifest[]>([])
const isLoading = ref(false)
const error = ref<string | null>(null)

export function usePipelines() {
  const searchQuery = ref('')
  const selectedTag = ref<string | null>(null)

  async function loadPipelines(force = false) {
    if (pipelines.value.length > 0 && !force) {
      return
    }
    isLoading.value = true
    error.value = null
    try {
      pipelines.value = await fetchPipelines()
    } catch (err: unknown) {
      error.value =
        err instanceof Error ? err.message : 'Failed to load pipelines'
    } finally {
      isLoading.value = false
    }
  }

  const allTags = computed(() => {
    const tagsSet = new Set<string>()
    for (const p of pipelines.value) {
      if (Array.isArray(p.tags)) {
        for (const t of p.tags) {
          tagsSet.add(t)
        }
      }
    }
    return Array.from(tagsSet).sort()
  })

  const filteredPipelines = computed(() => {
    const q = searchQuery.value.trim().toLowerCase()
    const tag = selectedTag.value

    return pipelines.value.filter((p) => {
      const matchesTag =
        !tag || (Array.isArray(p.tags) && p.tags.includes(tag))
      if (!matchesTag) return false

      if (!q) return true
      const matchesName = p.name.toLowerCase().includes(q)
      const matchesDesc = (p.description || '').toLowerCase().includes(q)
      const matchesId = p.id.toLowerCase().includes(q)
      return matchesName || matchesDesc || matchesId
    })
  })

  function getPipelineById(id: string): PipelineManifest | undefined {
    return pipelines.value.find((p) => p.id === id)
  }

  return {
    pipelines,
    isLoading,
    error,
    searchQuery,
    selectedTag,
    allTags,
    filteredPipelines,
    loadPipelines,
    getPipelineById,
  }
}
