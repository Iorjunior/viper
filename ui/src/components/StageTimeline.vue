<script setup lang="ts">
  import { computed } from 'vue'
  import type { PipelineStageConfig, StageRun } from '../api/types'

  const props = defineProps<{
    stages?: PipelineStageConfig[]
    stageRuns: StageRun[]
  }>()

  interface DisplayStage {
    id: string
    name: string
    status: 'pending' | 'running' | 'completed' | 'failed'
    error?: string | null
    output?: string
    startedAt?: string | null
    finishedAt?: string | null
    durationMs?: number | null
  }

  const displayStages = computed<DisplayStage[]>(() => {
    // If we have pipeline stages defined, use them as baseline order
    if (props.stages && props.stages.length > 0) {
      return props.stages.map((cfg) => {
        const run = props.stageRuns.find((r) => r.stage_id === cfg.id)
        let durationMs: number | null = null
        if (run?.started_at && run?.finished_at) {
          durationMs =
            new Date(run.finished_at).getTime() -
            new Date(run.started_at).getTime()
        }
        return {
          id: cfg.id,
          name: cfg.stage,
          status: (run?.status as DisplayStage['status']) || 'pending',
          error: run?.error,
          output: run?.output,
          startedAt: run?.started_at,
          finishedAt: run?.finished_at,
          durationMs,
        }
      })
    }

    // Fallback to whatever stage runs exist
    return props.stageRuns.map((run) => {
      let durationMs: number | null = null
      if (run.started_at && run.finished_at) {
        durationMs =
          new Date(run.finished_at).getTime() -
          new Date(run.started_at).getTime()
      }
      return {
        id: run.stage_id,
        name: run.stage_id,
        status: run.status as DisplayStage['status'],
        error: run.error,
        output: run.output,
        startedAt: run.started_at,
        finishedAt: run.finished_at,
        durationMs,
      }
    })
  })

  function formatDuration(ms: number | null | undefined): string {
    if (ms === null || ms === undefined || ms < 0) return ''
    if (ms < 1000) return `${ms}ms`
    const sec = (ms / 1000).toFixed(1)
    return `${sec}s`
  }
</script>

<template>
  <div
    class="relative pl-6 space-y-6 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-[var(--ui-border)]"
  >
    <div
      v-for="(st, idx) in displayStages"
      :key="st.id"
      class="relative group"
    >
      <!-- Timeline Node Marker -->
      <div
        class="absolute -left-6 top-1 w-5 h-5 rounded-full flex items-center justify-center border-2 transition-colors z-10"
        :class="[
          st.status === 'completed'
            ? 'bg-lime-500 border-lime-500 text-black'
            : st.status === 'running'
              ? 'bg-[var(--ui-bg)] border-lime-500 text-lime-500 animate-pulse ring-4 ring-lime-500/20'
              : st.status === 'failed'
                ? 'bg-red-500 border-red-500 text-white'
                : 'bg-[var(--ui-bg-muted)] border-[var(--ui-border)] text-neutral-400',
        ]"
      >
        <UIcon
          v-if="st.status === 'completed'"
          name="i-lucide-check"
          class="w-3 h-3 stroke-[3]"
        />
        <UIcon
          v-else-if="st.status === 'running'"
          name="i-lucide-loader-2"
          class="w-3 h-3 animate-spin stroke-[2.5]"
        />
        <UIcon
          v-else-if="st.status === 'failed'"
          name="i-lucide-x"
          class="w-3 h-3 stroke-[3]"
        />
        <span v-else class="text-[10px] font-bold">{{ idx + 1 }}</span>
      </div>

      <!-- Stage Card Content -->
      <div
        class="p-4 rounded-xl border border-[var(--ui-border)] bg-[var(--ui-bg)] shadow-xs transition-shadow"
        :class="{ 'ring-1 ring-lime-500/40': st.status === 'running' }"
      >
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-2">
            <span class="font-mono text-xs text-neutral-400"
              >#{{ st.id }}</span
            >
            <h4 class="font-semibold text-sm">{{ st.name }}</h4>
          </div>

          <div class="flex items-center space-x-2">
            <span
              v-if="st.durationMs"
              class="text-xs text-neutral-400 font-mono"
            >
              {{ formatDuration(st.durationMs) }}
            </span>
            <UBadge
              :color="
                st.status === 'completed'
                  ? 'success'
                  : st.status === 'running'
                    ? 'primary'
                    : st.status === 'failed'
                      ? 'error'
                      : 'neutral'
              "
              variant="subtle"
              size="sm"
            >
              {{ st.status }}
            </UBadge>
          </div>
        </div>

        <!-- Error display -->
        <div
          v-if="st.error"
          class="mt-3 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-600 dark:text-red-400 text-xs font-mono whitespace-pre-wrap"
        >
          {{ st.error }}
        </div>
      </div>
    </div>
  </div>
</template>
