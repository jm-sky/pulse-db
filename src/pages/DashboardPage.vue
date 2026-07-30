<script setup lang="ts">
import { Database } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import AuthenticatedLayout from '@/layouts/AuthenticatedLayout.vue'

const { t } = useI18n()
</script>

<template>
  <AuthenticatedLayout>
    <div class="flex flex-col items-center justify-center min-h-[60vh] space-y-4 text-center">
      <div class="rounded-full bg-primary/10 p-6">
        <Database class="size-16 text-primary" />
      </div>
      <h1 class="text-4xl font-bold">
        {{ t('dashboard.title', 'PulseDB') }}
      </h1>
      <p class="text-muted-foreground text-lg max-w-2xl">
        {{ t('dashboard.subtitle', 'Database performance diagnostics — domain modules coming next.') }}
      </p>
    </div>
  </AuthenticatedLayout>
</template>
