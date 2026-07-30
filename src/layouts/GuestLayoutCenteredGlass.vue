<script setup lang="ts">
import { useRoute } from 'vue-router'
import GuestLayoutFooter from '@/components/layout/GuestLayoutFooter.vue'
import LogoText from '@/components/ui/LogoText.vue'
import { PublicRouteNames } from '@/router/publicRoutes'
import DarkModeToggle from '@/shared/components/DarkModeToggle.vue'
import LocaleToggle from '@/shared/i18n/components/LocaleToggle.vue'

defineProps<{
  backgroundImage?: string
}>()

const route = useRoute()
const layoutActionsComponent = route.meta.layoutActionsComponent
</script>

<template>
  <div class="min-h-screen bg-linear-to-br from-blue-200 via-slate-100 to-purple-200 dark:from-gray-950 dark:via-gray-800 dark:to-gray-950 flex flex-col relative">
    <!-- Background image with smooth transitions -->
    <div
      v-if="backgroundImage"
      class="absolute inset-0 bg-cover bg-center transition-opacity duration-500"
      :style="{ backgroundImage: `url(${backgroundImage})` }"
    >
      <div class="absolute inset-0 bg-black/40 dark:bg-black/60 transition-colors duration-500" />
    </div>

    <!-- Fixed floating controls -->
    <nav class="fixed top-2 right-2 flex gap-2 rounded-lg p-2 bg-card/50 backdrop-blur-sm z-10">
      <slot name="actions">
        <component :is="layoutActionsComponent" v-if="layoutActionsComponent" />
      </slot>
      <LocaleToggle />
      <DarkModeToggle />
    </nav>

    <!-- Main content -->
    <main class="flex-1 flex flex-col items-center justify-center py-12 px-4 sm:px-6 lg:px-8 relative z-0">
      <!-- Logo -->
      <div class="mx-auto text-center mb-8">
        <RouterLink :to="{ name: PublicRouteNames.landing }" class="block hover:opacity-80 hover:scale-105 transition-all">
          <LogoText class="text-3xl drop-shadow" />
        </RouterLink>
      </div>

      <!-- Content with glass-morphism -->
      <div class="w-full max-w-md backdrop-blur-lg bg-white/60 dark:bg-gray-900/60 rounded-2xl shadow-2xl p-8">
        <slot />
      </div>
    </main>

    <!-- Footer -->
    <GuestLayoutFooter />
  </div>
</template>
