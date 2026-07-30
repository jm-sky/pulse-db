<script setup lang="ts">
import { Database } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import LandingLayout from '@/layouts/LandingLayout.vue'
import { useAuth } from '@/modules/auth/composables/useAuth'
import { AuthRoutePaths } from '@/modules/auth/config/routes'
import { config } from '@/shared/config/config'

const { t } = useI18n()
const router = useRouter()
const { isAuthenticated, user } = useAuth()

if (!config.backend.enabled) {
  router.replace({ name: 'home' })
}
</script>

<template>
  <LandingLayout>
    <div class="max-w-2xl w-full space-y-8 text-center">
      <div class="flex justify-center">
        <div class="rounded-full bg-primary/10 p-8">
          <Database class="size-20 text-primary" />
        </div>
      </div>

      <div class="space-y-4">
        <p v-if="isAuthenticated && user" class="text-2xl font-semibold text-muted-foreground">
          {{ t('landing.welcomeBack', { name: user.name }) }}
        </p>
        <h1 class="text-5xl font-bold tracking-tight">
          {{ t('landing.title', 'PulseDB') }}
        </h1>
        <p class="text-xl text-muted-foreground max-w-lg mx-auto">
          {{ t('landing.subtitle', 'Database performance diagnostics for PostgreSQL and SQL Server — self-hosted, API-first.') }}
        </p>
      </div>

      <div class="flex justify-center gap-4">
        <RouterLink
          :to="AuthRoutePaths.login"
          class="inline-flex items-center justify-center rounded-md bg-primary px-6 py-2 text-sm font-medium text-primary-foreground shadow hover:bg-primary/90 transition-colors"
        >
          {{ t('auth.login', 'Log In') }}
        </RouterLink>
      </div>
    </div>
  </LandingLayout>
</template>
