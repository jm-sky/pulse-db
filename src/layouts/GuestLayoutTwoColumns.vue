<script setup lang="ts">
import { Rocket } from 'lucide-vue-next'
import { useRoute } from 'vue-router'
import GuestLayoutFooter from '@/components/layout/GuestLayoutFooter.vue'
import LogoText from '@/components/ui/LogoText.vue'
import { PublicRouteNames } from '@/router/publicRoutes'
import DarkModeToggle from '@/shared/components/DarkModeToggle.vue'
import LocaleToggle from '@/shared/i18n/components/LocaleToggle.vue'

defineProps<{
  brandingTitle?: string
  brandingTagline?: string
  brandingMessage?: string
  backgroundImage?: string
}>()

const route = useRoute()
const layoutActionsComponent = route.meta.layoutActionsComponent
</script>

<template>
  <div class="min-h-screen grid lg:grid-cols-2 bg-gray-50 dark:bg-gray-950">
    <!-- Left Column - Branding Panel (hidden on mobile) -->
    <div class="hidden lg:flex relative bg-linear-to-br from-primary/90 to-primary-foreground/90 dark:from-primary/80 dark:via-purple-900 dark:to-primary-foreground/80">
      <!-- Background image overlay -->
      <div
        v-if="backgroundImage"
        class="absolute inset-0 bg-cover bg-center opacity-20"
        :style="{ backgroundImage: `url(${backgroundImage})` }"
      />

      <!-- Branding content -->
      <div class="relative z-10 flex flex-col justify-center items-center text-white p-12 w-full">
        <div class="max-w-md space-y-6 text-center">
          <!-- Logo -->
          <div class="mb-8">
            <LogoText class="text-4xl drop-shadow-lg" />
          </div>

          <!-- Title & Tagline -->
          <h1 class="text-3xl font-bold">
            {{ brandingTitle ?? 'Welcome to Vue Blocks Registry' }}
          </h1>
          <p class="text-lg opacity-90">
            {{ brandingTagline ?? 'Build faster with reusable Vue components' }}
          </p>

          <!-- Marketing message -->
          <div class="flex flex-col items-center justify-center gap-3 pt-6">
            <Rocket class="size-8" />
            <p class="text-base">
              {{ brandingMessage ?? 'Get started in minutes with our powerful component library' }}
            </p>
          </div>
        </div>
      </div>
    </div>

    <!-- Right Column - Content Area -->
    <div class="flex flex-col min-h-screen bg-white dark:bg-gray-900">
      <!-- Fixed dark mode button -->
      <div class="fixed flex items-center gap-2 top-4 right-4 z-10">
        <slot name="actions">
          <component :is="layoutActionsComponent" v-if="layoutActionsComponent" />
        </slot>
        <LocaleToggle />
        <DarkModeToggle />
      </div>

      <!-- Main content -->
      <main class="flex-1 flex flex-col items-center justify-center p-8 sm:p-12">
        <!-- Mobile logo (shown only on small screens) -->
        <div class="lg:hidden mb-8">
          <RouterLink :to="{ name: PublicRouteNames.landing }" class="block hover:opacity-80 hover:scale-105 transition-all">
            <LogoText class="text-2xl" />
          </RouterLink>
        </div>

        <!-- Content slot -->
        <div class="w-full max-w-md">
          <slot />
        </div>
      </main>

      <!-- Footer -->
      <GuestLayoutFooter />
    </div>
  </div>
</template>
