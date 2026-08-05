<script setup lang="ts">
import { subHours } from 'date-fns'
import { BarChart } from 'echarts/charts'
import {
  DataZoomComponent,
  GridComponent,
  LegendComponent,
  TooltipComponent,
} from 'echarts/components'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { computed, toRef } from 'vue'
import VChart from 'vue-echarts'
import { useI18n } from 'vue-i18n'
import { useWaitsTimelineQuery } from '@/modules/monitoring/composables/useMonitoringQueries'
import { useWorkspaceContext } from '@/modules/monitoring/composables/useWorkspaceContext'
import { buildWaitsChartOption } from '@/modules/monitoring/utils/waitsChartOption'

const props = defineProps<{
  instanceId: string
}>()

use([
  BarChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
  CanvasRenderer,
])

const { t } = useI18n()
const { selectedInstance, timeRangeLabel } = useWorkspaceContext()

const timelineParams = computed(() => {
  const end = new Date()
  const start = subHours(end, 1)
  return {
    start: start.toISOString(),
    end: end.toISOString(),
    granularity: '1m' as const,
  }
})

const instanceIdRef = toRef(props, 'instanceId')
const { data, isPending, isError, refetch, isFetching } = useWaitsTimelineQuery(
  instanceIdRef,
  timelineParams,
)

const chartOption = computed(() => {
  if (!data.value || data.value.series.length === 0) return undefined
  return buildWaitsChartOption(data.value)
})

const hasData = computed(() =>
  data.value?.series.some(series => series.points.length > 0) ?? false,
)

async function refresh() {
  await refetch()
}
</script>

<template>
  <div class="flex h-full min-h-0 flex-col gap-3 p-3">
    <div class="flex flex-wrap items-end justify-between gap-2">
      <div>
        <h1 class="text-base font-semibold tracking-tight">
          {{ t('monitoring.waits.title') }}
          <span v-if="selectedInstance" class="text-muted-foreground">
            — {{ selectedInstance.name }}
          </span>
        </h1>
        <p class="text-xs text-muted-foreground">
          {{ t('monitoring.waits.subtitle') }}
          <span class="text-border"> · </span>
          {{ timeRangeLabel }}
        </p>
      </div>
      <button
        type="button"
        class="rounded-md border border-border px-2 py-1 text-xs text-muted-foreground hover:bg-muted"
        :disabled="isFetching"
        @click="refresh"
      >
        {{ isFetching ? t('monitoring.waits.refreshing') : t('monitoring.waits.refresh') }}
      </button>
    </div>

    <div class="flex min-h-0 flex-1 flex-col rounded-md border border-border bg-background">
      <div v-if="isPending" class="flex flex-1 items-center justify-center text-sm text-muted-foreground">
        {{ t('monitoring.waits.loadingChart') }}
      </div>
      <div v-else-if="isError" class="flex flex-1 items-center justify-center text-sm text-destructive">
        {{ t('monitoring.waits.loadChartError') }}
      </div>
      <div v-else-if="!hasData || !chartOption" class="flex flex-1 items-center justify-center text-sm text-muted-foreground">
        {{ t('monitoring.waits.noData') }}
      </div>
      <VChart
        v-else
        class="min-h-[320px] w-full flex-1 max-h-[min(58vh,520px)]"
        :option="chartOption"
        autoresize
      />
    </div>
  </div>
</template>
