<script setup lang="ts">
  import { onMounted, computed, watch } from 'vue'
  import { useScrollLock } from '@vueuse/core'
  import { useSetup } from '../composables/useSetup'

  const {
    status,
    isLoading,
    error,
    activeStep,
    isSetupModalOpen,
    closeSetupModal,
    selectedMode,
    sttBackend,
    sttModel,
    llmBackend,
    ttsBackend,
    openaiBaseUrl,
    openaiApiKey,
    openaiModel,
    isTestingConnection,
    connectionResult,
    downloadingModelId,
    downloadError,
    isSubmitting,
    isAppleSilicon,
    hasCuda,
    applyPreset,
    loadStatus,
    testConnection,
    startDownload,
    finishSetup,
  } = useSetup()

  // Lock body scroll when modal is visible
  const isLocked = useScrollLock(
    typeof document !== 'undefined' ? document.body : null
  )
  watch(
    () => isSetupModalOpen.value,
    (val) => {
      isLocked.value = val
    },
    { immediate: true }
  )

  onMounted(() => {
    loadStatus()
  })

  function selectModeAndNext(mode: 'local' | 'cloud' | 'custom') {
    applyPreset(mode)
    activeStep.value = 2
  }

  async function onComplete() {
    await finishSetup()
  }

  const reviewModeLabel = computed(() => {
    if (selectedMode.value === 'local')
      return '100% Local AI (Offline & Private)'
    if (selectedMode.value === 'cloud') return 'Cloud AI (API Powered)'
    return 'Custom / Hybrid Configuration'
  })

  const reviewSttLabel = computed(() => {
    if (sttBackend.value === 'mlx_whisper') {
      return `MLX-Whisper (Apple Silicon Metal) • ${sttModel.value}`
    }
    if (sttBackend.value === 'faster_whisper') {
      return `Faster-Whisper (CUDA / CPU) • ${sttModel.value}`
    }
    if (sttBackend.value === 'openai') {
      return `OpenAI Cloud STT • ${sttModel.value}`
    }
    return `${sttBackend.value} (${sttModel.value})`
  })

  const reviewTtsLabel = computed(() => {
    if (ttsBackend.value === 'kokoro') {
      return 'Kokoro 82M (Local Neural Synthesis)'
    }
    if (ttsBackend.value === 'openai') {
      return 'OpenAI Cloud TTS'
    }
    return ttsBackend.value
  })

  const reviewLlmLabel = computed(() => {
    if (llmBackend.value === 'mlx_lm') {
      return `MLX-LM Local (${openaiModel.value || 'Qwen 2.5 1.5B'})`
    }
    if (llmBackend.value === 'openai') {
      if (
        openaiBaseUrl.value.includes('localhost') ||
        openaiBaseUrl.value.includes('11434') ||
        openaiBaseUrl.value.includes('127.0.0.1')
      ) {
        return `Ollama Local (${openaiModel.value || 'qwen2.5:1.5b'})`
      }
      return `OpenAI API (${openaiModel.value || 'gpt-4o-mini'})`
    }
    return `${llmBackend.value} (${openaiModel.value || 'Default'})`
  })

  const sttBackendOptions = [
    { label: 'Faster-Whisper (CUDA / CPU)', value: 'faster_whisper' },
    { label: 'MLX-Whisper (Apple Silicon Metal)', value: 'mlx_whisper' },
    { label: 'OpenAI Cloud STT', value: 'openai' },
  ]

  const sttModelOptions = [
    {
      label: 'large-v3-turbo (Recommended - ~1.5 GB)',
      value: 'large-v3-turbo',
    },
    { label: 'base (Fast & Lightweight - ~145 MB)', value: 'base' },
    { label: 'small (Balanced - ~480 MB)', value: 'small' },
  ]

  const ttsBackendOptions = [
    { label: 'Kokoro (Local Neural TTS - ~82 MB)', value: 'kokoro' },
    { label: 'OpenAI Cloud TTS', value: 'openai' },
  ]

  const llmBackendOptions = [
    { label: 'OpenAI / Ollama / OpenAI-Compatible', value: 'openai' },
    { label: 'MLX-LM (Apple Silicon Metal Local)', value: 'mlx_lm' },
  ]
</script>

<template>
  <UModal
    :open="isSetupModalOpen"
    :ui="{
      content: 'sm:max-w-3xl overflow-visible',
      body: 'space-y-6 overflow-visible max-h-[75vh] overflow-y-auto',
    }"
    :close="true"
    @update:open="(val: boolean) => (isSetupModalOpen = val)"
  >
    <!-- Modal Header with Title & Stepper -->
    <template #header>
      <div class="w-full space-y-4 pt-1">
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-3">
            <div
              class="w-10 h-10 rounded-2xl bg-lime-500/10 border border-lime-500/20 flex items-center justify-center text-lime-500"
            >
              <UIcon name="i-lucide-sparkles" class="w-5 h-5" />
            </div>
            <div>
              <h2 class="text-xl font-bold tracking-tight">Viper Setup</h2>
              <p class="text-xs text-neutral-500 dark:text-neutral-400">
                Configure your AI media processing engine and backends.
              </p>
            </div>
          </div>

          <UButton
            color="neutral"
            variant="ghost"
            size="sm"
            icon="i-lucide-x"
            aria-label="Close setup modal"
            @click="closeSetupModal()"
          />
        </div>

        <!-- Stepper Navigation -->
        <div class="flex items-center justify-between max-w-md mx-auto pt-1">
          <div
            v-for="step in [
              { num: 1, label: 'Mode' },
              { num: 2, label: 'Providers' },
              { num: 3, label: 'Models' },
              { num: 4, label: 'Review' },
            ]"
            :key="step.num"
            class="flex flex-col items-center cursor-pointer group"
            @click="activeStep = step.num"
          >
            <div
              class="w-8 h-8 rounded-full flex items-center justify-center font-bold text-xs transition-all"
              :class="[
                activeStep === step.num
                  ? 'bg-lime-500 text-neutral-950 ring-4 ring-lime-500/20 shadow-md scale-105'
                  : activeStep > step.num
                    ? 'bg-lime-500/20 text-lime-500 border border-lime-500/30'
                    : 'bg-neutral-100 dark:bg-neutral-800 text-neutral-400 border border-[var(--ui-border)]',
              ]"
            >
              <UIcon
                v-if="activeStep > step.num"
                name="i-lucide-check"
                class="w-4 h-4 stroke-[2.5]"
              />
              <span v-else>{{ step.num }}</span>
            </div>
            <span
              class="text-[11px] font-semibold mt-1 tracking-tight transition-colors"
              :class="
                activeStep === step.num
                  ? 'text-lime-500 font-bold'
                  : 'text-neutral-500 group-hover:text-neutral-900 dark:group-hover:text-neutral-200'
              "
            >
              {{ step.label }}
            </span>
          </div>
        </div>
      </div>
    </template>

    <!-- Modal Body -->
    <template #body>
      <!-- Loading State -->
      <div
        v-if="isLoading"
        class="p-8 text-center border border-[var(--ui-border)] rounded-2xl bg-[var(--ui-bg)] animate-pulse"
      >
        <div
          class="h-6 w-36 bg-neutral-200 dark:bg-neutral-800 rounded mx-auto mb-3"
        />
        <div
          class="h-4 w-72 bg-neutral-200 dark:bg-neutral-800 rounded mx-auto"
        />
      </div>

      <!-- STEP 1: Environment & Mode Selection -->
      <div v-else-if="activeStep === 1" class="space-y-5">
        <!-- Hardware Diagnostics Banner -->
        <div
          v-if="status?.hardware"
          class="p-4 rounded-2xl border border-[var(--ui-border)] bg-neutral-50 dark:bg-neutral-900/40 flex items-center justify-between gap-3 text-xs"
        >
          <div class="flex items-center space-x-3">
            <div
              class="w-8 h-8 rounded-xl bg-lime-500/10 border border-lime-500/20 flex items-center justify-center text-lime-500 shrink-0"
            >
              <UIcon
                :name="
                  isAppleSilicon
                    ? 'i-lucide-cpu'
                    : hasCuda
                      ? 'i-lucide-zap'
                      : 'i-lucide-monitor'
                "
                class="w-4 h-4"
              />
            </div>
            <div>
              <span class="font-bold text-neutral-900 dark:text-neutral-100">
                {{
                  isAppleSilicon
                    ? 'Apple Silicon (Metal & MLX Accelerated)'
                    : hasCuda
                      ? 'NVIDIA CUDA Detected'
                      : 'Standard CPU Environment'
                }}
              </span>
              <span class="text-neutral-400 ml-1.5 font-mono">
                {{ status.hardware.platform }}/{{ status.hardware.machine }}
              </span>
            </div>
          </div>

          <UBadge color="primary" size="xs" variant="subtle">
            Suggested: {{ status.hardware.recommended_mode.toUpperCase() }}
          </UBadge>
        </div>

        <!-- Mode Cards Grid -->
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <!-- 100% Local -->
          <div
            class="p-5 rounded-2xl border transition-all cursor-pointer flex flex-col justify-between group hover:border-lime-500/80"
            :class="[
              selectedMode === 'local'
                ? 'border-lime-500 bg-lime-500/5 ring-2 ring-lime-500/20'
                : 'border-[var(--ui-border)] bg-[var(--ui-bg)]',
            ]"
            @click="applyPreset('local')"
          >
            <div class="space-y-3">
              <div
                class="w-10 h-10 rounded-xl flex items-center justify-center transition-colors"
                :class="
                  selectedMode === 'local'
                    ? 'bg-lime-500 text-neutral-950 font-bold'
                    : 'bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-400'
                "
              >
                <UIcon name="i-lucide-shield-check" class="w-5 h-5" />
              </div>
              <div>
                <h3 class="text-base font-bold">100% Local</h3>
                <p
                  class="text-xs text-neutral-500 dark:text-neutral-400 mt-1 leading-relaxed"
                >
                  Offline & private. Models run directly on your hardware.
                </p>
              </div>
            </div>
            <div class="pt-4 mt-2">
              <UButton
                :color="selectedMode === 'local' ? 'primary' : 'neutral'"
                :variant="selectedMode === 'local' ? 'solid' : 'outline'"
                size="sm"
                class="w-full justify-center"
                @click.stop="selectModeAndNext('local')"
              >
                Select Local
              </UButton>
            </div>
          </div>

          <!-- Cloud / API -->
          <div
            class="p-5 rounded-2xl border transition-all cursor-pointer flex flex-col justify-between group hover:border-lime-500/80"
            :class="[
              selectedMode === 'cloud'
                ? 'border-lime-500 bg-lime-500/5 ring-2 ring-lime-500/20'
                : 'border-[var(--ui-border)] bg-[var(--ui-bg)]',
            ]"
            @click="applyPreset('cloud')"
          >
            <div class="space-y-3">
              <div
                class="w-10 h-10 rounded-xl flex items-center justify-center transition-colors"
                :class="
                  selectedMode === 'cloud'
                    ? 'bg-lime-500 text-neutral-950 font-bold'
                    : 'bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-400'
                "
              >
                <UIcon name="i-lucide-cloud" class="w-5 h-5" />
              </div>
              <div>
                <h3 class="text-base font-bold">Cloud APIs</h3>
                <p
                  class="text-xs text-neutral-500 dark:text-neutral-400 mt-1 leading-relaxed"
                >
                  Cloud execution via OpenAI APIs. Minimal RAM required.
                </p>
              </div>
            </div>
            <div class="pt-4 mt-2">
              <UButton
                :color="selectedMode === 'cloud' ? 'primary' : 'neutral'"
                :variant="selectedMode === 'cloud' ? 'solid' : 'outline'"
                size="sm"
                class="w-full justify-center"
                @click.stop="selectModeAndNext('cloud')"
              >
                Select Cloud
              </UButton>
            </div>
          </div>

          <!-- Custom / Hybrid -->
          <div
            class="p-5 rounded-2xl border transition-all cursor-pointer flex flex-col justify-between group hover:border-lime-500/80"
            :class="[
              selectedMode === 'custom'
                ? 'border-lime-500 bg-lime-500/5 ring-2 ring-lime-500/20'
                : 'border-[var(--ui-border)] bg-[var(--ui-bg)]',
            ]"
            @click="applyPreset('custom')"
          >
            <div class="space-y-3">
              <div
                class="w-10 h-10 rounded-xl flex items-center justify-center transition-colors"
                :class="
                  selectedMode === 'custom'
                    ? 'bg-lime-500 text-neutral-950 font-bold'
                    : 'bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-400'
                "
              >
                <UIcon name="i-lucide-sliders" class="w-5 h-5" />
              </div>
              <div>
                <h3 class="text-base font-bold">Custom / Hybrid</h3>
                <p
                  class="text-xs text-neutral-500 dark:text-neutral-400 mt-1 leading-relaxed"
                >
                  Mix local models with Ollama, vLLM or OpenAI endpoints.
                </p>
              </div>
            </div>
            <div class="pt-4 mt-2">
              <UButton
                :color="selectedMode === 'custom' ? 'primary' : 'neutral'"
                :variant="selectedMode === 'custom' ? 'solid' : 'outline'"
                size="sm"
                class="w-full justify-center"
                @click.stop="selectModeAndNext('custom')"
              >
                Select Custom
              </UButton>
            </div>
          </div>
        </div>
      </div>

      <!-- STEP 2: Providers & Credentials -->
      <div v-else-if="activeStep === 2" class="space-y-5">
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <!-- STT Backend -->
          <div class="space-y-1">
            <label
              class="block text-xs font-semibold uppercase tracking-wider text-neutral-500"
            >
              Speech-to-Text (STT) Backend
            </label>
            <USelect
              v-model="sttBackend"
              :items="sttBackendOptions"
              class="w-full"
            />
          </div>

          <!-- STT Model -->
          <div class="space-y-1">
            <label
              class="block text-xs font-semibold uppercase tracking-wider text-neutral-500"
            >
              Whisper Model Variant
            </label>
            <USelect
              v-model="sttModel"
              :items="sttModelOptions"
              class="w-full"
            />
          </div>

          <!-- TTS Backend -->
          <div class="space-y-1">
            <label
              class="block text-xs font-semibold uppercase tracking-wider text-neutral-500"
            >
              Text-to-Speech (TTS) Backend
            </label>
            <USelect
              v-model="ttsBackend"
              :items="ttsBackendOptions"
              class="w-full"
            />
          </div>

          <!-- LLM Backend -->
          <div class="space-y-1">
            <label
              class="block text-xs font-semibold uppercase tracking-wider text-neutral-500"
            >
              Translation LLM Backend
            </label>
            <USelect
              v-model="llmBackend"
              :items="llmBackendOptions"
              class="w-full"
            />
          </div>
        </div>

        <!-- Cloud / OpenAI / Ollama Settings -->
        <div
          v-if="
            llmBackend === 'openai' ||
            sttBackend === 'openai' ||
            ttsBackend === 'openai' ||
            selectedMode !== 'local'
          "
          class="pt-4 border-t border-[var(--ui-border)] space-y-3"
        >
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div class="space-y-1">
              <label
                class="block text-[11px] font-semibold uppercase tracking-wider text-neutral-500"
              >
                Base URL (Blank for OpenAI, or Ollama URL)
              </label>
              <UInput
                v-model="openaiBaseUrl"
                placeholder="e.g. http://localhost:11434/v1"
                class="w-full"
              />
            </div>

            <div class="space-y-1">
              <label
                class="block text-[11px] font-semibold uppercase tracking-wider text-neutral-500"
              >
                API Key (Required for OpenAI)
              </label>
              <UInput
                v-model="openaiApiKey"
                type="password"
                placeholder="sk-..."
                class="w-full"
              />
            </div>

            <div class="space-y-1 sm:col-span-2">
              <label
                class="block text-[11px] font-semibold uppercase tracking-wider text-neutral-500"
              >
                Model Identifier
              </label>
              <UInput
                v-model="openaiModel"
                placeholder="gpt-4o-mini or qwen2.5:1.5b"
                class="w-full"
              />
            </div>
          </div>

          <div class="flex items-center gap-3 pt-1">
            <UButton
              color="neutral"
              variant="outline"
              size="xs"
              icon="i-lucide-activity"
              :loading="isTestingConnection"
              @click="testConnection()"
            >
              Test Connection
            </UButton>

            <span
              v-if="connectionResult"
              class="text-xs font-medium flex items-center gap-1.5"
              :class="
                connectionResult.success
                  ? 'text-lime-600 dark:text-lime-400'
                  : 'text-red-500'
              "
            >
              <UIcon
                :name="
                  connectionResult.success
                    ? 'i-lucide-check-circle'
                    : 'i-lucide-alert-circle'
                "
                class="w-4 h-4"
              />
              <span>{{ connectionResult.message }}</span>
            </span>
          </div>
        </div>
      </div>

      <!-- STEP 3: Local AI Models -->
      <div v-else-if="activeStep === 3" class="space-y-4">
        <div class="flex items-center justify-between">
          <span class="text-xs text-neutral-500">
            Pre-cache model weights for zero-latency execution.
          </span>
          <UButton
            color="neutral"
            variant="ghost"
            size="xs"
            icon="i-lucide-refresh-cw"
            @click="loadStatus()"
          >
            Refresh
          </UButton>
        </div>

        <UAlert
          v-if="downloadError"
          color="error"
          icon="i-lucide-alert-triangle"
          :title="downloadError"
        />

        <div
          class="grid grid-cols-1 sm:grid-cols-2 gap-3 max-h-64 overflow-y-auto pr-1"
        >
          <div
            v-for="model in status?.models || []"
            :key="model.id"
            class="p-3.5 rounded-xl border border-[var(--ui-border)] bg-[var(--ui-bg-muted)]/40 flex flex-col justify-between space-y-2"
          >
            <div>
              <div class="flex items-start justify-between">
                <span class="font-bold text-xs">{{ model.name }}</span>
                <UBadge
                  :color="model.downloaded ? 'primary' : 'neutral'"
                  :variant="model.downloaded ? 'solid' : 'subtle'"
                  size="xs"
                >
                  {{ model.downloaded ? 'Ready' : 'Pending' }}
                </UBadge>
              </div>
              <p
                class="text-[11px] text-neutral-500 dark:text-neutral-400 mt-0.5 leading-relaxed"
              >
                {{ model.description }}
              </p>
            </div>

            <div
              class="flex items-center justify-between pt-1.5 border-t border-[var(--ui-border)]/40 text-[11px]"
            >
              <span class="text-neutral-400 font-mono">{{
                model.size_label
              }}</span>
              <UButton
                v-if="!model.downloaded"
                color="primary"
                variant="subtle"
                size="xs"
                icon="i-lucide-download"
                :loading="downloadingModelId === model.id"
                @click="startDownload(model.id)"
              >
                Download
              </UButton>
              <span
                v-else
                class="text-lime-600 dark:text-lime-400 font-semibold flex items-center gap-1"
              >
                <UIcon name="i-lucide-check-circle" class="w-3.5 h-3.5" />
                <span>Cached</span>
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- STEP 4: Review & Finish -->
      <div v-else-if="activeStep === 4" class="space-y-4">
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div
            class="p-3.5 rounded-xl border border-[var(--ui-border)] bg-[var(--ui-bg-muted)]/30 space-y-1"
          >
            <span
              class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500"
            >
              Operation Mode
            </span>
            <p class="text-xs font-bold">{{ reviewModeLabel }}</p>
          </div>

          <div
            class="p-3.5 rounded-xl border border-[var(--ui-border)] bg-[var(--ui-bg-muted)]/30 space-y-1"
          >
            <span
              class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500"
            >
              Speech-to-Text
            </span>
            <p class="text-xs font-bold">{{ reviewSttLabel }}</p>
          </div>

          <div
            class="p-3.5 rounded-xl border border-[var(--ui-border)] bg-[var(--ui-bg-muted)]/30 space-y-1"
          >
            <span
              class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500"
            >
              Text-to-Speech
            </span>
            <p class="text-xs font-bold">{{ reviewTtsLabel }}</p>
          </div>

          <div
            class="p-3.5 rounded-xl border border-[var(--ui-border)] bg-[var(--ui-bg-muted)]/30 space-y-1"
          >
            <span
              class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500"
            >
              Translation LLM
            </span>
            <p class="text-xs font-bold">{{ reviewLlmLabel }}</p>
          </div>
        </div>

        <UAlert
          v-if="error"
          color="error"
          icon="i-lucide-alert-circle"
          :title="error"
        />
      </div>
    </template>

    <!-- Modal Footer with Back & Next / Save actions -->
    <template #footer>
      <div class="w-full flex items-center justify-between">
        <UButton
          v-if="activeStep > 1"
          color="neutral"
          variant="ghost"
          size="sm"
          icon="i-lucide-arrow-left"
          @click="activeStep--"
        >
          Back
        </UButton>
        <div v-else />

        <div class="flex items-center space-x-2">
          <UButton
            v-if="activeStep < 4"
            color="primary"
            size="sm"
            icon="i-lucide-arrow-right"
            @click="activeStep++"
          >
            {{
              activeStep === 1
                ? 'Next: Providers'
                : activeStep === 2
                  ? 'Next: Models'
                  : 'Next: Review'
            }}
          </UButton>

          <UButton
            v-else
            color="primary"
            size="sm"
            icon="i-lucide-check-circle"
            :loading="isSubmitting"
            @click="onComplete()"
          >
            Save & Launch Viper
          </UButton>
        </div>
      </div>
    </template>
  </UModal>
</template>
