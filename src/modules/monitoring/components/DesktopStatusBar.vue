<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useWorkspaceContext } from '@/modules/monitoring/composables/useWorkspaceContext'
import type { CollectorStatus } from '@/modules/monitoring/mocks/instances'

const { t } = useI18n()
const { selectedInstance, timeRangeLabel } = useWorkspaceContext()

const collectorLabel = computed(() => {
  const status: CollectorStatus = selectedInstance.value?.collectorStatus ?? 'unknown'
  if (status === 'ok') return t('monitoring.status.collectorOk')
  if (status === 'degraded') return t('monitoring.status.collectorDegraded')
  return t('monitoring.status.collectorUnknown')
})

const engineLabel = computed(() => {
  const engine = selectedInstance.value?.engine
  if (!engine) return t('monitoring.status.noInstance')
  return t(`monitoring.status.engine.${engine}`)
})

const lastSample = computed(() => {
  const raw = selectedInstance.value?.lastSampleAt
  if (!raw) return '—'
  try {
    return new Date(raw).toLocaleString()
  } catch {
    return raw
  }
})
</script>

<template>
  <footer class="flex h-6 shrink-0 items-center gap-3 border-t border-border bg-muted/50 px-2 font-mono text-[11px] text-muted-foreground">
    <span class="rounded bg-muted px-1 text-[10px] uppercase tracking-wide">
      {{ t('monitoring.status.mock') }}
    </span>
    <span class="truncate">{{ selectedInstance?.name ?? t('monitoring.status.noInstance') }}</span>
    <span class="text-border">|</span>
    <span>{{ engineLabel }}</span>
    <span class="text-border">|</span>
    <span
      :class="{
        'text-success': selectedInstance?.collectorStatus === 'ok',
        'text-chart-4': selectedInstance?.collectorStatus === 'degraded',
      }"
    >
      {{ collectorLabel }}
    </span>
    <span class="text-border">|</span>
    <span>{{ timeRangeLabel }}</span>
    <span class="ml-auto truncate">{{ lastSample }}</span>
  </footer>
</template>
