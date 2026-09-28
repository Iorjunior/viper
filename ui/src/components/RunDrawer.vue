<script setup lang="ts">
  import { ref, computed, watch } from 'vue'
  import { useRouter } from 'vue-router'
  import { triggerRun } from '../api/pipelines'
  import type { PipelineManifest, PipelineInput, Run } from '../api/types'

  const props = defineProps<{
    open: boolean
    pipeline: PipelineManifest | null
  }>()

  const emit = defineEmits<{
    (e: 'update:open', val: boolean): void
    (e: 'submitted', run: Run): void
  }>()

  const router = useRouter()
  const isSubmitting = ref(false)
  const errorMessage = ref<string | null>(null)
  const formValues = ref<
    Record<string, string | number | boolean | undefined>
  >({})

  interface NormalizedInput {
    name: string
    label: string
    type: string
    default?: unknown
    options?: string[]
  }

  const normalizedInputs = computed<NormalizedInput[]>(() => {
    if (!props.pipeline || !props.pipeline.inputs) return []

    const raw = props.pipeline.inputs
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

  watch(
    () => props.pipeline,
    () => {
      const initial: Record<string, string | number | boolean | undefined> = {}
      for (const input of normalizedInputs.value) {
        if (input.default !== undefined) {
          initial[input.name] = input.default as
            string | number | boolean | undefined
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
    },
    { immediate: true }
  )

  async function onSubmit() {
    if (!props.pipeline) return
    isSubmitting.value = true
    errorMessage.value = null

    try {
      const run = await triggerRun(props.pipeline.id, formValues.value)
      emit('submitted', run)
      emit('update:open', false)
      router.push(`/runs/${run.id}`)
    } catch (err: unknown) {
      errorMessage.value =
        err instanceof Error ? err.message : 'Failed to trigger run'
    } finally {
      isSubmitting.value = false
    }
  }
</script>

<template>
  <USlideover
    :open="open"
    :title="pipeline ? `Run: ${pipeline.name}` : 'Run Pipeline'"
    :description="pipeline?.description"
    @update:open="(val: boolean) => emit('update:open', val)"
  >
    <template #body>
      <form
        v-if="pipeline"
        id="run-form"
        class="space-y-5"
        @submit.prevent="onSubmit"
      >
        <!-- Error Alert -->
        <UAlert
          v-if="errorMessage"
          color="error"
          variant="subtle"
          icon="i-lucide-alert-circle"
          :title="errorMessage"
        />

        <!-- Dynamic Inputs -->
        <div
          v-for="input in normalizedInputs"
          :key="input.name"
          class="space-y-1.5"
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

          <!-- Boolean / Switch -->
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

          <!-- Text / URL / File Input -->
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
          class="text-sm text-neutral-500 py-4 italic"
        >
          This pipeline does not require any custom inputs. Ready to run.
        </div>
      </form>
    </template>

    <template #footer>
      <div class="flex items-center justify-end space-x-3 w-full">
        <UButton
          color="neutral"
          variant="outline"
          :disabled="isSubmitting"
          @click="emit('update:open', false)"
        >
          Cancel
        </UButton>
        <UButton
          color="primary"
          icon="i-lucide-play"
          type="submit"
          form="run-form"
          :loading="isSubmitting"
        >
          Start Execution
        </UButton>
      </div>
    </template>
  </USlideover>
</template>
