import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useSetup } from './useSetup'
import * as setupApi from '../api/setup'
import type { SetupStatus } from '../api/types'

const mockStatus: SetupStatus = {
  setup_completed: false,
  hardware: {
    platform: 'Darwin',
    machine: 'arm64',
    device: 'apple_silicon',
    is_apple_silicon: true,
    has_cuda: false,
    recommended_mode: 'local',
  },
  models: [
    {
      id: 'kokoro-82m',
      name: 'Kokoro 82M',
      capability: 'tts',
      repo_id: 'hexgrad/Kokoro-82M',
      size_label: '~82 MB',
      description: 'TTS',
      downloaded: true,
    },
    {
      id: 'whisper-large-v3-turbo',
      name: 'Whisper Large',
      capability: 'stt',
      repo_id: 'mlx-community/whisper-large-v3-turbo',
      size_label: '~1.5 GB',
      description: 'STT',
      downloaded: false,
    },
  ],
  current_config: {
    stt_backend: 'mlx_whisper',
    stt_model: 'large-v3-turbo',
    llm_backend: 'mlx_lm',
    tts_backend: 'kokoro',
    openai_base_url: '',
    openai_model: 'gpt-4o-mini',
    has_openai_key: false,
  },
}

describe('useSetup', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('loads setup status and detects Apple Silicon hardware', async () => {
    vi.spyOn(setupApi, 'fetchSetupStatus').mockResolvedValue(mockStatus)
    const { loadStatus, status, isAppleSilicon, selectedMode } = useSetup()

    await loadStatus()
    expect(status.value?.setup_completed).toBe(false)
    expect(isAppleSilicon.value).toBe(true)
    expect(selectedMode.value).toBe('local')
  })

  it('applies local and cloud presets correctly', async () => {
    vi.spyOn(setupApi, 'fetchSetupStatus').mockResolvedValue(mockStatus)
    const { loadStatus, applyPreset, selectedMode, sttBackend, ttsBackend } =
      useSetup()

    await loadStatus()

    // Switch to cloud
    applyPreset('cloud')
    expect(selectedMode.value).toBe('cloud')
    expect(sttBackend.value).toBe('openai')
    expect(ttsBackend.value).toBe('openai')

    // Switch to local
    applyPreset('local')
    expect(selectedMode.value).toBe('local')
    expect(sttBackend.value).toBe('mlx_whisper')
    expect(ttsBackend.value).toBe('kokoro')
  })

  it('tests external API connection successfully', async () => {
    vi.spyOn(setupApi, 'validateConnection').mockResolvedValue({
      success: true,
      message: 'Verified',
      models_available: ['gpt-4o'],
    })

    const { testConnection, connectionResult, isTestingConnection } = useSetup()
    expect(isTestingConnection.value).toBe(false)

    const promise = testConnection()
    await promise

    expect(connectionResult.value?.success).toBe(true)
    expect(connectionResult.value?.models_available).toContain('gpt-4o')
  })

  it('downloads model and refreshes status', async () => {
    vi.spyOn(setupApi, 'fetchSetupStatus').mockResolvedValue(mockStatus)
    const downloadSpy = vi.spyOn(setupApi, 'downloadModel').mockResolvedValue({
      success: true,
      model_id: 'whisper-large-v3-turbo',
      message: 'Done',
    })

    const { startDownload, downloadingModelId } = useSetup()
    expect(downloadingModelId.value).toBeNull()

    await startDownload('whisper-large-v3-turbo')
    expect(downloadSpy).toHaveBeenCalledWith('whisper-large-v3-turbo')
    expect(downloadingModelId.value).toBeNull()
  })

  it('completes setup successfully', async () => {
    vi.spyOn(setupApi, 'fetchSetupStatus').mockResolvedValue(mockStatus)
    const completeSpy = vi.spyOn(setupApi, 'completeSetup').mockResolvedValue({
      success: true,
      message: 'Setup completed',
    })

    const { finishSetup, loadStatus, status } = useSetup()
    await loadStatus()
    const success = await finishSetup()

    expect(success).toBe(true)
    expect(completeSpy).toHaveBeenCalled()
    expect(status.value?.setup_completed).toBe(true)
  })
})
