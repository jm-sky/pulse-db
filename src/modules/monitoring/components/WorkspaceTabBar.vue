<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { cn } from '@/lib/utils'

defineProps<{
  activeTab: 'waits'
}>()

const { t } = useI18n()
</script>

<template>
  <div class="flex h-8 shrink-0 items-end gap-0 border-b border-border bg-muted/40 px-1">
    <div
      :class="cn(
        'relative flex h-7 items-center border border-b-0 border-border px-3 text-xs',
        'rounded-t-md bg-background text-foreground',
      )"
    >
      {{ t('monitoring.tabs.waits') }}
    </div>
  </div>
</template>
