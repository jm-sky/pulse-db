<script setup lang="ts">
import AppFooter from '@/components/layout/AppFooter.vue'
import DarkModeToggle from '@/shared/components/DarkModeToggle.vue'
import LocaleToggle from '@/shared/i18n/components/LocaleToggle.vue'
</script>

<template>
  <div class="min-h-screen flex flex-col bg-linear-to-br from-background to-muted relative">
    <!-- Fixed controls in top right -->
    <nav class="fixed top-2 right-2 flex gap-2 rounded-lg p-2 bg-card/50 backdrop-blur-sm z-10">
      <LocaleToggle />
      <DarkModeToggle />
    </nav>

    <!-- Main Content -->
    <main class="flex-1 flex flex-col items-center justify-center gap-8 p-4">
      <slot />
    </main>

    <!-- Footer -->
    <AppFooter />
  </div>
</template>

