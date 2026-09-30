import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import ui from '@nuxt/ui/vue-plugin'
import App from './App.vue'

describe('App', () => {
  it('mounts without crashing', async () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/', component: { template: '<div>Gallery</div>' } },
        { path: '/runs', component: { template: '<div>Runs</div>' } },
        { path: '/builder', component: { template: '<div>Builder</div>' } },
        { path: '/setup', component: { template: '<div>Setup</div>' } },
      ],
    })

    const wrapper = mount(App, {
      global: {
        plugins: [router, ui],
      },
    })
    await router.isReady()
    expect(wrapper.exists()).toBe(true)
  })
})
