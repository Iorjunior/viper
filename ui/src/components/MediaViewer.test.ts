import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ui from '@nuxt/ui/vue-plugin'
import MediaViewer from './MediaViewer.vue'

describe('MediaViewer', () => {
  it('detects video and audio assets from outputs JSON', () => {
    const outputs = JSON.stringify({
      video: '/data/output.mp4',
      audio: '/data/soundtrack.mp3',
    })

    const wrapper = mount(MediaViewer, {
      props: {
        outputsJson: outputs,
      },
      global: {
        plugins: [ui],
      },
    })

    const videoEl = wrapper.find('video')
    expect(videoEl.exists()).toBe(true)
    expect(videoEl.attributes('src')).toContain('/api/assets/data/output.mp4')

    const audioEl = wrapper.find('audio')
    expect(audioEl.exists()).toBe(true)
    expect(audioEl.attributes('src')).toContain(
      '/api/assets/data/soundtrack.mp3'
    )
  })
})
