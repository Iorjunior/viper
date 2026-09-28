<script setup lang="ts">
  import { ref, computed, watch, onMounted } from 'vue'
  import { useRoute, useRouter } from 'vue-router'
  import { usePipelines } from '../composables/usePipelines'
  import { triggerRun } from '../api/pipelines'
  import type { PipelineManifest, PipelineInput } from '../api/types'

  const route = useRoute()
  const router = useRouter()
  const { pipelines, isLoading: isLoadingPipelines, loadPipelines } = usePipelines()

  const selectedPipelineId = ref<string>('')
  const isSubmitting = ref(false)
  const errorMessage = ref<string | null>(null)
  const formValues = ref<Record<string, string | number | boolean | undefined>>({})

  interface NormalizedInput {
    name: string
    label: string
    type: string
    default?: unknown
    options?: string[]
  }

  const selectedPipeline = computed<PipelineManifest | null>(() => {
    return pipelines.value.find((p) => p.id === selectedPipelineId.value) || null
  })

  const pipelineOptions = computed(() => {
    return pipelines.value.map((p) => ({
      label: p.name,
      value: p.id,
    }))
  })

  const normalizedInputs = computed<NormalizedInput[]>(() => {
    if (!selectedPipeline.value || !selectedPipeline.value.inputs) return []

    const raw = selectedPipeline.value.inputs
    if (Array.isArray(raw)) {
      return raw.map((item: PipelineInput) => ({
        name: item.name,
        label: item.label || item.name,
        type: item.type || 'string',
        default: item.default,
        options: item.options || [],
      }))
    }

    return Object.entries(raw).map(([key, val]) => {
      const item = (
        typeof val === 'object' && val !== null ? val : {}
      ) as Record<string, unknown>
      return {
        name: key,
        label: (item.label as string) || key,
        type: (item.type as string) || 'string',
        default: item.default,
        options: Array.isArray(item.options) ? (item.options as string[]) : [],
      }
    })
  })

  function initFormValues() {
    const initial: Record<string, string | number | boolean | undefined> = {}
    for (const input of normalizedInputs.value) {
      if (input.default !== undefined) {
        initial[input.name] = input.default as
          | string
          | number
          | boolean
          | undefined
      } else if (
        input.type === 'select' &&
        input.options &&
        input.options.length > 0
      ) {
        initial[input.name] = input.options[0]
      } else if (input.type === 'boolean') {
        initial[input.name] = false
      } else {
        initial[input.name] = ''
      }
    }
    formValues.value = initial
    errorMessage.value = null
  }

  watch(
    () => selectedPipeline.value,
    () => {
      initFormValues()
    },
    { immediate: true }
  )

  onMounted(async () => {
    await loadPipelines()
    const queryPipeline = (route.query.pipeline as string) || (route.params.pipelineId as string)
    if (queryPipeline && pipelines.value.some((p) => p.id === queryPipeline)) {
      selectedPipelineId.value = queryPipeline
    } else if (pipelines.value.length > 0) {
      selectedPipelineId.value = pipelines.value[0].id
    }
  })

  watch(
    () => route.query.pipeline,
    (newVal) => {
      if (newVal && typeof newVal === 'string') {
        selectedPipelineId.value = newVal
      }
    }
  )

  async function onSubmit() {
    if (!selectedPipeline.value) return
    isSubmitting.value = true
    errorMessage.value = null

    try {
      const run = await triggerRun(selectedPipeline.value.id, formValues.value)
      router.push(`/runs/${run.id}`)
    } catch (err: unknown) {
      errorMessage.value =
        err instanceof Error ? err.message : 'Failed to trigger pipeline run'
    } finally {
      isSubmitting.value = false
    }
  }
</script>

<template>
  <div class="max-w-3xl mx-auto space-y-8">
    <!-- Navigation & Title -->
    <div class="space-y-3">
      <router-link
        to="/"
        class="inline-flex items-center space-x-1.5 text-xs font-semibold text-neutral-500 hover:text-neutral-900 dark:hover:text-neutral-100 transition-colors"
      >
        <UIcon name="i-lucide-arrow-left" class="w-4 h-4" />
        <span>Back to Gallery</span>
      </router-link>

      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-3xl font-extrabold tracking-tight">Run Pipeline</h1>
          <p class="text-sm text-neutral-500 dark:text-neutral-400 mt-1">
            Configure parameters and trigger pipeline execution.
          </p>
        </div>
      </div>
    </div>

    <!-- Loading Skeleton -->
    <div v-if="isLoadingPipelines && !selectedPipeline" class="space-y-6 animate-pulse">
      <div class="h-28 rounded-2xl bg-[var(--ui-bg-muted)]" />
      <div class="h-64 rounded-2xl bg-[var(--ui-bg-muted)]" />
    </div>

    <!-- Main Content -->
    <div v-else class="space-y-6">
      <!-- Pipeline Selector Card -->
      <div
        class="p-6 rounded-2xl border border-[var(--ui-border)] bg-[var(--ui-bg)] shadow-xs space-y-4"
      >
        <div class="space-y-1.5">
          <label
            class="block text-xs font-semibold uppercase tracking-wider text-neutral-500 dark:text-neutral-400"
          >
            Select Pipeline
          </label>
          <USelect
            :model-value="selectedPipelineId"
            :items="pipelineOptions"
            class="w-full"
            @update:model-value="(val: unknown) => { selectedPipelineId = String(val ?? '') }"
          />
        </div>

        <div v-if="selectedPipeline" class="pt-3 border-t border-[var(--ui-border)]/50 space-y-2">
          <div class="flex items-center space-x-2">
            <h2 class="text-lg font-bold">{{ selectedPipeline.name }}</h2>
            <UBadge v-if="selectedPipeline.builtin" color="neutral" variant="subtle" size="xs">
              Builtin
            </UBadge>
          </div>
          <p class="text-sm text-neutral-500 dark:text-neutral-400 leading-relaxed">
            {{ selectedPipeline.description }}
          </p>
          <div class="flex items-center gap-3 text-xs text-neutral-400 font-mono pt-1">
            <span>{{ selectedPipeline.stages.length }} stages</span>
            <span>•</span>
            <span>ID: {{ selectedPipeline.id }}</span>
          </div>
        </div>
      </div>

      <!-- Execution Form -->
      <div
        class="p-6 rounded-2xl border border-[var(--ui-border)] bg-[var(--ui-bg)] shadow-xs"
      >
        <form id="run-form" class="space-y-6" @submit.prevent="onSubmit">
          <!-- Error Alert -->
          <UAlert
            v-if="errorMessage"
            color="error"
            variant="subtle"
            icon="i-lucide-alert-circle"
            :title="errorMessage"
          />

          <!-- Dynamic Form Inputs -->
          <div
            v-for="input in normalizedInputs"
            :key="input.name"
            class="space-y-2"
          >
            <label
              class="block text-xs font-semibold uppercase tracking-wider text-neutral-500 dark:text-neutral-400"
            >
              {{ input.label }}
            </label>

            <!-- Select Input -->
            <USelect
              v-if="input.type === 'select'"
              :model-value="String(formValues[input.name] ?? '')"
              :items="input.options || []"
              class="w-full"
              @update:model-value="
                (val: unknown) => {
                  formValues[input.name] = String(val ?? '')
                }
              "
            />

            <!-- Boolean Switch -->
            <div
              v-else-if="input.type === 'boolean'"
              class="flex items-center space-x-2 pt-1"
            >
              <USwitch
                :model-value="Boolean(formValues[input.name])"
                @update:model-value="
                  (val: boolean) => {
                    formValues[input.name] = val
                  }
                "
              />
              <span class="text-sm font-medium">{{ input.label }}</span>
            </div>

            <!-- Text / URL Input -->
            <UInput
              v-else
              :model-value="String(formValues[input.name] ?? '')"
              class="w-full"
              :placeholder="`Enter ${input.label.toLowerCase()}...`"
              @update:model-value="
                (val: string | number) => {
                  formValues[input.name] = String(val ?? '')
                }
              "
            />
          </div>

          <div
            v-if="normalizedInputs.length === 0"
            class="text-sm text-neutral-500 py-3 italic"
          >
            This pipeline does not require custom inputs. Ready to execute.
          </div>

          <!-- Action Buttons -->
          <div class="flex items-center justify-end space-x-3 pt-4 border-t border-[var(--ui-border)]">
            <router-link to="/">
              <UButton color="neutral" variant="outline" :disabled="isSubmitting">
                Cancel
              </UButton>
            </router-link>
            <UButton
              color="primary"
              icon="i-lucide-play"
              type="submit"
              :loading="isSubmitting"
            >
              Start Execution
            </UButton>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>
