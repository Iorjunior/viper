<script setup lang="ts">
  import { onMounted } from 'vue'
  import { usePipelines } from '../composables/usePipelines'
  import type { PipelineManifest } from '../api/types'

  const {
    isLoading,
    error,
    searchQuery,
    selectedTag,
    allTags,
    filteredPipelines,
    loadPipelines,
  } = usePipelines()

  function getPipelineIcon(pipeline: PipelineManifest): string {
    const id = pipeline.id.toLowerCase()
    const tags = Array.isArray(pipeline.tags)
      ? pipeline.tags.map((t) => t.toLowerCase())
      : []

    if (id.includes('dubbing') || tags.includes('dubbing')) {
      return 'i-lucide-mic'
    }
    if (id.includes('video') || tags.includes('video')) {
      return 'i-lucide-video'
    }
    if (
      id.includes('audio') ||
      tags.includes('audio') ||
      tags.includes('vocals')
    ) {
      return 'i-lucide-audio-waveform'
    }
    if (
      id.includes('transcri') ||
      tags.includes('transcription') ||
      tags.includes('speech')
    ) {
      return 'i-lucide-file-text'
    }
    if (id.includes('translat') || tags.includes('translation')) {
      return 'i-lucide-languages'
    }
    return 'i-lucide-layers'
  }

  onMounted(() => {
    loadPipelines()
  })
</script>

<template>
  <div class="space-y-8 w-full">
    <!-- Hero / Title -->
    <div
      class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4"
    >
      <div>
        <h1 class="text-3xl font-extrabold tracking-tight">
          Pipeline Gallery
        </h1>
        <p class="text-sm text-neutral-500 dark:text-neutral-400 mt-1">
          Explore and execute local AI media processing pipelines.
        </p>
      </div>

      <router-link to="/builder">
        <UButton color="primary" icon="i-lucide-plus" size="md">
          New Pipeline
        </UButton>
      </router-link>
    </div>

    <!-- Search & Filter Bar -->
    <div class="flex flex-col sm:flex-row gap-4 items-center justify-between">
      <div class="w-full sm:w-96">
        <UInput
          v-model="searchQuery"
          icon="i-lucide-search"
          placeholder="Search pipelines..."
          class="w-full"
        />
      </div>

      <!-- Tag Filters -->
      <div class="flex items-center gap-1.5 flex-wrap w-full sm:w-auto">
        <UButton
          size="xs"
          :color="selectedTag === null ? 'primary' : 'neutral'"
          :variant="selectedTag === null ? 'solid' : 'ghost'"
          @click="selectedTag = null"
        >
          All
        </UButton>
        <UButton
          v-for="tag in allTags"
          :key="tag"
          size="xs"
          :color="selectedTag === tag ? 'primary' : 'neutral'"
          :variant="selectedTag === tag ? 'solid' : 'ghost'"
          @click="selectedTag = selectedTag === tag ? null : tag"
        >
          #{{ tag }}
        </UButton>
      </div>
    </div>

    <!-- Loading State -->
    <div
      v-if="isLoading"
      class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-6"
    >
      <div
        v-for="i in 10"
        :key="i"
        class="h-56 rounded-2xl border border-[var(--ui-border)] bg-[var(--ui-bg-muted)] animate-pulse"
      />
    </div>

    <!-- Error State -->
    <UAlert
      v-else-if="error"
      color="error"
      icon="i-lucide-alert-triangle"
      :title="error"
    />

    <!-- Empty State -->
    <div
      v-else-if="filteredPipelines.length === 0"
      class="text-center py-16 border border-dashed border-[var(--ui-border)] rounded-2xl p-8"
    >
      <UIcon
        name="i-lucide-inbox"
        class="w-12 h-12 text-neutral-400 mx-auto stroke-1"
      />
      <h3 class="mt-4 text-base font-semibold">No pipelines found</h3>
      <p class="mt-1 text-sm text-neutral-500">
        Try adjusting your search query or tag filters.
      </p>
    </div>

    <!-- Pipelines Grid -->
    <div
      v-else
      class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-6"
    >
      <div
        v-for="pipeline in filteredPipelines"
        :key="pipeline.id"
        class="p-6 rounded-2xl border border-[var(--ui-border)] bg-[var(--ui-bg)] hover:border-lime-500/50 hover:shadow-lg hover:shadow-lime-500/5 transition-all duration-200 flex flex-col justify-between group"
      >
        <div class="space-y-4">
          <!-- Card Header -->
          <div class="flex items-start justify-between">
            <div
              class="w-11 h-11 rounded-xl bg-lime-500/10 border border-lime-500/20 flex items-center justify-center text-lime-500"
            >
              <UIcon :name="getPipelineIcon(pipeline)" class="w-5 h-5" />
            </div>
            <UBadge
              v-if="pipeline.builtin"
              color="neutral"
              variant="subtle"
              size="xs"
            >
              Builtin
            </UBadge>
          </div>

          <!-- Title & Description -->
          <div>
            <h3
              class="font-bold text-lg tracking-tight group-hover:text-lime-500 transition-colors"
            >
              {{ pipeline.name }}
            </h3>
            <p
              class="text-sm text-neutral-500 dark:text-neutral-400 mt-1 line-clamp-2 leading-relaxed"
            >
              {{ pipeline.description || 'No description provided.' }}
            </p>
          </div>

          <!-- Tags -->
          <div
            v-if="pipeline.tags && pipeline.tags.length > 0"
            class="flex flex-wrap gap-1.5 pt-1"
          >
            <span
              v-for="tag in pipeline.tags"
              :key="tag"
              class="text-[11px] font-medium px-2 py-0.5 rounded-md bg-[var(--ui-bg-muted)] text-neutral-600 dark:text-neutral-400"
            >
              {{ tag }}
            </span>
          </div>
        </div>

        <!-- Card Footer -->
        <div
          class="pt-6 mt-6 border-t border-[var(--ui-border)] flex items-center justify-between"
        >
          <span class="text-xs text-neutral-400 font-mono">
            {{ pipeline.stages.length }} stages
          </span>

          <router-link :to="{ path: '/new', query: { pipeline: pipeline.id } }">
            <UButton
              color="primary"
              size="sm"
              icon="i-lucide-play"
            >
              Run Pipeline
            </UButton>
          </router-link>
        </div>
      </div>
    </div>
  </div>
</template>
