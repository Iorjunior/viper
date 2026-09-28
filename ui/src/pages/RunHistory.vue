<script setup lang="ts">
  import { onMounted, onUnmounted } from 'vue'
  import { useRouter } from 'vue-router'
  import { useRuns } from '../composables/useRuns'
  import type { Run } from '../api/types'

  const router = useRouter()
  const { runs, isLoading, error, loadRuns } = useRuns()

  let historyPollTimer: ReturnType<typeof setInterval> | null = null

  onMounted(async () => {
    await loadRuns()
    historyPollTimer = setInterval(() => {
      const hasActive = runs.value.some(
        (r) => r.status === 'pending' || r.status === 'running'
      )
      if (hasActive) {
        loadRuns()
      }
    }, 2500)
  })

  onUnmounted(() => {
    if (historyPollTimer) {
      clearInterval(historyPollTimer)
      historyPollTimer = null
    }
  })

  function formatDateTime(isoStr: string | null): string {
    if (!isoStr) return '-'
    try {
      const d = new Date(isoStr)
      return d.toLocaleString()
    } catch {
      return isoStr
    }
  }

  function calculateDuration(run: Run): string {
    if (!run.created_at || !run.finished_at) return '-'
    try {
      const start = new Date(run.created_at).getTime()
      const end = new Date(run.finished_at).getTime()
      const diffMs = end - start
      if (diffMs < 1000) return `${diffMs}ms`
      return `${(diffMs / 1000).toFixed(1)}s`
    } catch {
      return '-'
    }
  }

  function getStatusColor(status: string) {
    switch (status.toLowerCase()) {
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
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-3xl font-extrabold tracking-tight">
          Execution History
        </h1>
        <p class="text-sm text-neutral-500 dark:text-neutral-400 mt-1">
          Review and inspect previous pipeline executions.
        </p>
      </div>

      <UButton
        color="neutral"
        variant="outline"
        icon="i-lucide-refresh-cw"
        :loading="isLoading"
        @click="loadRuns()"
      >
        Refresh
      </UButton>
    </div>

    <!-- Error Alert -->
    <UAlert
      v-if="error"
      color="error"
      icon="i-lucide-alert-triangle"
      :title="error"
    />

    <!-- Empty State -->
    <div
      v-else-if="!isLoading && runs.length === 0"
      class="text-center py-16 border border-dashed border-[var(--ui-border)] rounded-2xl p-8"
    >
      <UIcon
        name="i-lucide-history"
        class="w-12 h-12 text-neutral-400 mx-auto stroke-1"
      />
      <h3 class="mt-4 text-base font-semibold">No runs recorded yet</h3>
      <p class="mt-1 text-sm text-neutral-500">
        Trigger a pipeline from the gallery to see results here.
      </p>
      <div class="mt-6">
        <router-link to="/">
          <UButton color="primary">Go to Gallery</UButton>
        </router-link>
      </div>
    </div>

    <!-- Runs List Table -->
    <div
      v-else
      class="rounded-2xl border border-[var(--ui-border)] bg-[var(--ui-bg)] overflow-hidden shadow-xs"
    >
      <div class="overflow-x-auto">
        <table class="w-full text-left text-sm">
          <thead
            class="border-b border-[var(--ui-border)] bg-[var(--ui-bg-muted)] text-xs uppercase font-semibold text-neutral-500"
          >
            <tr>
              <th class="px-6 py-3.5">Run ID</th>
              <th class="px-6 py-3.5">Pipeline</th>
              <th class="px-6 py-3.5">Status</th>
              <th class="px-6 py-3.5">Created At</th>
              <th class="px-6 py-3.5">Duration</th>
              <th class="px-6 py-3.5 text-right">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-[var(--ui-border)]">
            <tr
              v-for="run in runs"
              :key="run.id"
              class="hover:bg-[var(--ui-bg-muted)]/50 transition-colors cursor-pointer group"
              @click="router.push(`/runs/${run.id}`)"
            >
              <td
                class="px-6 py-4 font-mono text-xs font-semibold text-lime-500"
              >
                {{ run.id.slice(0, 8) }}...
              </td>
              <td class="px-6 py-4 font-medium">
                {{ run.pipeline_id }}
              </td>
              <td class="px-6 py-4">
                <UBadge
                  :color="getStatusColor(run.status)"
                  variant="subtle"
                  size="sm"
                >
                  {{ run.status }}
                </UBadge>
              </td>
              <td class="px-6 py-4 text-xs text-neutral-400">
                {{ formatDateTime(run.created_at) }}
              </td>
              <td class="px-6 py-4 font-mono text-xs text-neutral-400">
                {{ calculateDuration(run) }}
              </td>
              <td class="px-6 py-4 text-right" @click.stop>
                <router-link :to="`/runs/${run.id}`">
                  <UButton
                    size="xs"
                    color="neutral"
                    variant="ghost"
                    icon="i-lucide-arrow-right"
                  >
                    View
                  </UButton>
                </router-link>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
