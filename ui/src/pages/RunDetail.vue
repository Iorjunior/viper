<script setup lang="ts">
  import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
  import { useRoute } from 'vue-router'
  import { useRuns } from '../composables/useRuns'
  import { useWebSocket } from '../composables/useWebSocket'
  import { fetchPipeline } from '../api/pipelines'
  import StageTimeline from '../components/StageTimeline.vue'
  import MediaViewer from '../components/MediaViewer.vue'
  import type { PipelineManifest, WsStageEvent } from '../api/types'

  const route = useRoute()
  const runId = computed(() => route.params.id as string)

  const {
    currentRun,
    isLoadingDetail,
    detailError,
    loadRunDetail,
    startPolling,
    stopPolling,
    applyWsEvent,
  } = useRuns()

  const pipelineManifest = ref<PipelineManifest | null>(null)
  const activeTab = ref<'media' | 'inputs' | 'raw'>('media')
  const liveEvents = ref<WsStageEvent[]>([])

  const { isConnected } = useWebSocket(runId, {
    onEvent: (event) => {
      liveEvents.value.unshift(event)
      applyWsEvent(event)
    },
  })

  async function init() {
    if (!runId.value) return
    const run = await loadRunDetail(runId.value)
    if (run?.pipeline_id) {
      try {
        pipelineManifest.value = await fetchPipeline(run.pipeline_id)
      } catch {
        // Pipeline may have been custom or removed
      }
    }
    if (run && (run.status === 'pending' || run.status === 'running')) {
      startPolling(runId.value)
    } else {
      stopPolling()
    }
  }

  onMounted(() => {
    init()
  })

  watch(runId, () => {
    init()
  })

  onUnmounted(() => {
    stopPolling()
  })

  const parsedInputs = computed(() => {
    if (!currentRun.value?.inputs) return {}
    try {
      return JSON.parse(currentRun.value.inputs)
    } catch {
      return {}
    }
  })

  function getStatusColor(status: string) {
    switch (status?.toLowerCase()) {
      case 'completed':
        return 'success'
      case 'running':
        return 'primary'
      case 'failed':
        return 'error'
      case 'cancelled':
        return 'warning'
      default:
        return 'neutral'
    }
  }
</script>

<template>
  <div class="space-y-6">
    <!-- Top Action Bar -->
    <div class="flex items-center justify-between">
      <router-link
        to="/runs"
        class="inline-flex items-center space-x-1.5 text-xs font-semibold text-neutral-500 hover:text-neutral-900 dark:hover:text-neutral-100 transition-colors"
      >
        <UIcon name="i-lucide-arrow-left" class="w-4 h-4" />
        <span>Back to Runs</span>
      </router-link>

      <!-- Live WS Indicator -->
      <div class="flex items-center space-x-2 text-xs">
        <span
          class="w-2 h-2 rounded-full"
          :class="isConnected ? 'bg-lime-500 animate-pulse' : 'bg-neutral-400'"
        />
        <span class="text-neutral-400 font-medium">
          {{ isConnected ? 'Live stream connected' : 'Connecting stream...' }}
        </span>
      </div>
    </div>

    <!-- Error State -->
    <UAlert
      v-if="detailError"
      color="error"
      icon="i-lucide-alert-triangle"
      :title="detailError"
    />

    <!-- Loading Skeleton -->
    <div
      v-else-if="isLoadingDetail && !currentRun"
      class="space-y-6 animate-pulse"
    >
      <div class="h-28 rounded-2xl bg-[var(--ui-bg-muted)]" />
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-8">
        <div class="lg:col-span-5 h-96 rounded-2xl bg-[var(--ui-bg-muted)]" />
        <div class="lg:col-span-7 h-96 rounded-2xl bg-[var(--ui-bg-muted)]" />
      </div>
    </div>

    <!-- Main Run Content -->
    <div v-else-if="currentRun" class="space-y-8">
      <!-- Run Hero Header -->
      <div
        class="p-6 rounded-2xl border border-[var(--ui-border)] bg-[var(--ui-bg)] shadow-xs flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4"
      >
        <div class="space-y-1">
          <div class="flex items-center space-x-2.5">
            <h1 class="text-2xl font-extrabold tracking-tight">
              {{ pipelineManifest?.name || currentRun.pipeline_id }}
            </h1>
            <UBadge
              :color="getStatusColor(currentRun.status)"
              variant="subtle"
              size="md"
            >
              {{ currentRun.status }}
            </UBadge>
          </div>
          <div
            class="flex items-center space-x-3 text-xs text-neutral-400 font-mono"
          >
            <span>Run: {{ currentRun.id }}</span>
            <span>•</span>
            <span
              >Started:
              {{ new Date(currentRun.created_at).toLocaleTimeString() }}</span
            >
          </div>
        </div>

        <div class="flex items-center space-x-3">
          <UButton
            color="neutral"
            variant="outline"
            size="sm"
            icon="i-lucide-rotate-cw"
            @click="init()"
          >
            Refresh
          </UButton>
        </div>
      </div>

      <!-- Two-Column Layout -->
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        <!-- Left Column: Stage Progression & Inputs (3-5 cols on wide) -->
        <div class="lg:col-span-5 xl:col-span-4 2xl:col-span-3 space-y-6">
          <div
            class="p-6 rounded-2xl border border-[var(--ui-border)] bg-[var(--ui-bg)] shadow-xs space-y-5"
          >
            <h3
              class="font-bold text-sm tracking-tight flex items-center justify-between"
            >
              <span>Pipeline Stages</span>
              <span class="font-mono text-xs text-neutral-400">
                {{ currentRun.stage_runs.length }} executed
              </span>
            </h3>

            <StageTimeline
              :stages="pipelineManifest?.stages"
              :stage-runs="currentRun.stage_runs"
            />
          </div>

          <!-- Inputs Summary -->
          <div
            class="p-6 rounded-2xl border border-[var(--ui-border)] bg-[var(--ui-bg)] shadow-xs space-y-4"
          >
            <h3 class="font-bold text-sm tracking-tight">Input Parameters</h3>
            <div class="space-y-2">
              <div
                v-for="(val, key) in parsedInputs"
                :key="key"
                class="flex items-center justify-between text-xs py-1.5 border-b border-[var(--ui-border)]/50 last:border-none"
              >
                <span class="font-mono text-neutral-500 uppercase">{{
                  key
                }}</span>
                <span class="font-medium truncate max-w-xs text-right">{{
                  val
                }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Right Column: Outputs, Live Log & Media Player (7-9 cols on wide) -->
        <div class="lg:col-span-7 xl:col-span-8 2xl:col-span-9 space-y-6">
          <!-- View Switcher -->
          <div
            class="flex items-center space-x-2 border-b border-[var(--ui-border)] pb-3"
          >
            <UButton
              size="sm"
              :color="activeTab === 'media' ? 'primary' : 'neutral'"
              :variant="activeTab === 'media' ? 'solid' : 'ghost'"
              icon="i-lucide-play-circle"
              @click="activeTab = 'media'"
            >
              Output Media
            </UButton>
            <UButton
              size="sm"
              :color="activeTab === 'raw' ? 'primary' : 'neutral'"
              :variant="activeTab === 'raw' ? 'solid' : 'ghost'"
              icon="i-lucide-code"
              @click="activeTab = 'raw'"
            >
              Full JSON
            </UButton>
          </div>

          <!-- Tab: Media Outputs -->
          <div v-if="activeTab === 'media'">
            <MediaViewer :outputs-json="currentRun.outputs" />
          </div>

          <!-- Tab: Raw JSON Details -->
          <div
            v-else-if="activeTab === 'raw'"
            class="p-6 rounded-2xl border border-[var(--ui-border)] bg-[var(--ui-bg)]"
          >
            <pre
              class="p-4 rounded-xl bg-neutral-900 text-lime-400 text-xs font-mono overflow-x-auto leading-relaxed max-h-[600px]"
              >{{ JSON.stringify(currentRun, null, 2) }}</pre>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
