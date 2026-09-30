<script setup lang="ts">
  import AppHeader from './components/AppHeader.vue'
  import SetupModal from './components/SetupModal.vue'
</script>

<template>
  <UApp>
    <div
      class="min-h-screen bg-[var(--ui-bg)] text-[var(--ui-text)] flex flex-col font-sans transition-colors duration-200"
    >
      <AppHeader />
      <main class="flex-1 w-full px-4 sm:px-6 lg:px-8 py-6">
        <router-view />
      </main>
      <SetupModal />
    </div>
  </UApp>
</template>
