<script setup lang="ts">
  import { useRoute } from 'vue-router'
  import { useDark, useToggle } from '@vueuse/core'

  const isDark = useDark()
  const toggleDark = useToggle(isDark)
  const route = useRoute()
</script>

<template>
  <header
    class="sticky top-0 z-40 border-b border-[var(--ui-border)] bg-[var(--ui-bg)]/80 backdrop-blur w-full"
  >
    <div
      class="w-full px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between"
    >
      <!-- Brand & Navigation -->
      <div class="flex items-center space-x-8">
        <router-link to="/" class="flex items-center space-x-2.5 group">
          <div
            class="w-9 h-9 rounded-xl bg-lime-500/20 border border-lime-500/40 flex items-center justify-center text-lime-500 group-hover:bg-lime-500/30 transition-colors"
          >
            <UIcon
              name="i-lucide-play"
              class="w-5 h-5 text-lime-500 fill-current"
            />
          </div>
          <div>
            <span class="font-bold text-lg tracking-tight">VIPER</span>
          </div>
        </router-link>

        <nav class="hidden md:flex items-center space-x-1">
          <router-link
            to="/"
            class="px-3 py-1.5 rounded-lg text-sm font-medium transition-colors"
            :class="
              route?.path === '/'
                ? 'bg-lime-500/15 text-lime-600 dark:text-lime-400 font-semibold'
                : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100 hover:bg-neutral-100 dark:hover:bg-neutral-800'
            "
          >
            Pipelines
          </router-link>

          <router-link
            to="/runs"
            class="px-3 py-1.5 rounded-lg text-sm font-medium transition-colors"
            :class="
              route?.path?.startsWith('/runs')
                ? 'bg-lime-500/15 text-lime-600 dark:text-lime-400 font-semibold'
                : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100 hover:bg-neutral-100 dark:hover:bg-neutral-800'
            "
          >
            Runs
          </router-link>

          <router-link
            to="/builder"
            class="px-3 py-1.5 rounded-lg text-sm font-medium transition-colors"
            :class="
              route?.path === '/builder'
                ? 'bg-lime-500/15 text-lime-600 dark:text-lime-400 font-semibold'
                : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100 hover:bg-neutral-100 dark:hover:bg-neutral-800'
            "
          >
            Builder
          </router-link>
        </nav>
      </div>

      <!-- Right actions: Theme -->
      <div class="flex items-center space-x-3">
        <UButton
          color="neutral"
          variant="ghost"
          size="sm"
          :icon="isDark ? 'i-lucide-sun' : 'i-lucide-moon'"
          aria-label="Toggle theme"
          @click="toggleDark()"
        />
      </div>
    </div>
  </header>
</template>
