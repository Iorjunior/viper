import { ref, computed } from 'vue'
import {
  fetchSetupStatus,
  validateConnection,
  downloadModel,
  completeSetup,
} from '../api/setup'
import type {
  SetupStatus,
  ValidateConnectionResponse,
  CompleteSetupRequest,
} from '../api/types'

const isSetupModalOpen = ref(false)

export function useSetup() {
  const status = ref<SetupStatus | null>(null)
  const isLoading = ref<boolean>(false)
  const error = ref<string | null>(null)
  const activeStep = ref<number>(1)

  function openSetupModal() {
    isSetupModalOpen.value = true
  }

  function closeSetupModal() {
    isSetupModalOpen.value = false
  }

  // Configuration Form
  const selectedMode = ref<'local' | 'cloud' | 'custom'>('local')
  const sttBackend = ref<string>('auto')
  const sttModel = ref<string>('large-v3-turbo')
  const llmBackend = ref<string>('auto')
  const ttsBackend = ref<string>('kokoro')
  const openaiBaseUrl = ref<string>('')
  const openaiApiKey = ref<string>('')
  const openaiModel = ref<string>('gpt-4o-mini')

  // Connection Testing
  const isTestingConnection = ref<boolean>(false)
  const connectionResult = ref<ValidateConnectionResponse | null>(null)

  // Model Download
  const downloadingModelId = ref<string | null>(null)
  const downloadError = ref<string | null>(null)
  const isSubmitting = ref<boolean>(false)

  const isAppleSilicon = computed(
    () => status.value?.hardware.is_apple_silicon ?? false
  )
  const hasCuda = computed(() => status.value?.hardware.has_cuda ?? false)

  function applyPreset(mode: 'local' | 'cloud' | 'custom') {
    selectedMode.value = mode
    if (mode === 'local') {
      ttsBackend.value = 'kokoro'
      sttModel.value = 'large-v3-turbo'
      if (isAppleSilicon.value) {
        sttBackend.value = 'mlx_whisper'
        llmBackend.value = 'mlx_lm'
        openaiBaseUrl.value = ''
        openaiModel.value = 'Qwen2.5-1.5B-Instruct-4bit'
      } else {
        sttBackend.value = 'faster_whisper'
        llmBackend.value = 'openai'
        openaiBaseUrl.value = 'http://localhost:11434/v1'
        openaiModel.value = 'qwen2.5:1.5b'
      }
    } else if (mode === 'cloud') {
      sttBackend.value = 'openai'
      sttModel.value = 'whisper-1'
      llmBackend.value = 'openai'
      ttsBackend.value = 'openai'
      openaiBaseUrl.value = ''
      openaiModel.value = 'gpt-4o-mini'
    }
  }

  async function loadStatus() {
    isLoading.value = true
    error.value = null
    try {
      const data = await fetchSetupStatus()
      status.value = data

      if (!data.setup_completed) {
        const initialMode =
          data.hardware.recommended_mode === 'cloud' ? 'cloud' : 'local'
        applyPreset(initialMode)
        isSetupModalOpen.value = true
      } else if (data.current_config) {
        // Resolve stored config or fallback from auto
        const isMac = data.hardware.is_apple_silicon
        sttBackend.value =
          data.current_config.stt_backend === 'auto'
            ? isMac
              ? 'mlx_whisper'
              : 'faster_whisper'
            : data.current_config.stt_backend || 'auto'
        sttModel.value = data.current_config.stt_model || 'large-v3-turbo'
        llmBackend.value =
          data.current_config.llm_backend === 'auto'
            ? isMac
              ? 'mlx_lm'
              : 'openai'
            : data.current_config.llm_backend || 'auto'
        ttsBackend.value = data.current_config.tts_backend || 'kokoro'
        openaiBaseUrl.value = data.current_config.openai_base_url || ''
        openaiModel.value = data.current_config.openai_model || 'gpt-4o-mini'
      }
    } catch (err: unknown) {
      error.value =
        err instanceof Error ? err.message : 'Failed to retrieve setup status.'
    } finally {
      isLoading.value = false
    }
  }

  async function testConnection() {
    isTestingConnection.value = true
    connectionResult.value = null
    try {
      const res = await validateConnection({
        provider: 'openai',
        base_url: openaiBaseUrl.value || undefined,
        api_key: openaiApiKey.value || undefined,
        model: openaiModel.value || undefined,
      })
      connectionResult.value = res
    } catch (err: unknown) {
      connectionResult.value = {
        success: false,
        message:
          err instanceof Error
            ? err.message
            : 'Network error verifying endpoint.',
      }
    } finally {
      isTestingConnection.value = false
    }
  }

  async function startDownload(modelId: string) {
    downloadingModelId.value = modelId
    downloadError.value = null
    try {
      await downloadModel(modelId)
      // Refresh status to reflect updated cached state
      await loadStatus()
    } catch (err: unknown) {
      downloadError.value =
        err instanceof Error
          ? err.message
          : `Failed to download model ${modelId}`
    } finally {
      downloadingModelId.value = null
    }
  }

  async function finishSetup(): Promise<boolean> {
    isSubmitting.value = true
    error.value = null
    try {
      const payload: CompleteSetupRequest = {
        mode: selectedMode.value,
        stt_backend: sttBackend.value,
        stt_model: sttModel.value,
        llm_backend: llmBackend.value,
        tts_backend: ttsBackend.value,
        openai_base_url: openaiBaseUrl.value || undefined,
        openai_api_key: openaiApiKey.value || undefined,
        openai_model: openaiModel.value || undefined,
      }
      await completeSetup(payload)
      isSetupModalOpen.value = false
      if (status.value) {
        status.value.setup_completed = true
      }
      return true
    } catch (err: unknown) {
      error.value =
        err instanceof Error ? err.message : 'Failed to save setup preferences.'
      return false
    } finally {
      isSubmitting.value = false
    }
  }

  return {
    status,
    isLoading,
    error,
    activeStep,
    isSetupModalOpen,
    openSetupModal,
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
  }
}
