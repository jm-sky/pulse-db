<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { MOCK_WAIT_SERIES } from '@/modules/monitoring/mocks/instances'

const { t } = useI18n()

const columns = computed(() => {
  const len = MOCK_WAIT_SERIES[0]?.values.length ?? 0
  return Array.from({ length: len }, (_, i) => {
    const segments = MOCK_WAIT_SERIES.map(series => ({
      key: series.key,
      color: series.color,
      value: series.values[i] ?? 0,
    }))
    const total = segments.reduce((sum, s) => sum + s.value, 0)
    return { segments, total: total || 1 }
  })
})
</script>

<template>
  <div class="flex h-full min-h-0 flex-col gap-3 p-3">
    <div class="flex flex-wrap items-end justify-between gap-2">
      <div>
        <h1 class="text-base font-semibold tracking-tight">
          {{ t('monitoring.waits.title') }}
        </h1>
        <p class="text-xs text-muted-foreground">
          {{ t('monitoring.waits.subtitle') }}
        </p>
      </div>
      <p class="max-w-md text-right text-[11px] text-muted-foreground">
        {{ t('monitoring.waits.placeholderNote') }}
      </p>
    </div>

    <div class="flex min-h-0 flex-1 flex-col rounded-md border border-border bg-background">
      <div class="flex flex-1 items-end gap-1 px-3 pb-2 pt-6">
        <div
          v-for="(col, idx) in columns"
          :key="idx"
          class="flex h-full min-h-40 flex-1 flex-col-reverse justify-start"
          :title="t('monitoring.waits.drillHint')"
        >
          <div
            v-for="seg in col.segments"
            :key="seg.key"
            class="w-full opacity-90 transition-opacity hover:opacity-100"
            :class="seg.color"
            :style="{ height: `${(seg.value / col.total) * 100}%`, minHeight: seg.value > 0 ? '2px' : '0' }"
          />
        </div>
      </div>
      <div class="flex items-center justify-between border-t border-border px-3 py-1.5 text-[10px] text-muted-foreground">
        <span>−60m</span>
        <span>−30m</span>
        <span>now</span>
      </div>
    </div>

    <div class="flex flex-wrap items-center gap-3 text-xs">
      <span class="text-muted-foreground">{{ t('monitoring.waits.legend') }}:</span>
      <span
        v-for="series in MOCK_WAIT_SERIES"
        :key="series.key"
        class="inline-flex items-center gap-1.5"
      >
        <span class="size-2.5 rounded-sm" :class="series.color" />
        {{ series.key }}
      </span>
    </div>
  </div>
</template>
