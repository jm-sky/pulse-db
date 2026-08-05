<script setup lang="ts">
import { subHours } from 'date-fns'
import { computed, ref, toRef } from 'vue'
import { useI18n } from 'vue-i18n'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { cn } from '@/lib/utils'
import { useQueryPeriodComparisonQuery } from '@/modules/monitoring/composables/useMonitoringQueries'
import { useWorkspaceContext } from '@/modules/monitoring/composables/useWorkspaceContext'
import {
  formatCalls,
  formatDeltaPct,
  formatMs,
  truncateSql,
} from '@/modules/monitoring/utils/formatQueryMetrics'

const props = defineProps<{
  instanceId: string
}>()

const { t } = useI18n()
const { selectedInstance } = useWorkspaceContext()

const regressionsOnly = ref(false)

const comparisonParams = computed(() => {
  const currentEnd = new Date()
  const currentStart = subHours(currentEnd, 24)
  const baselineEnd = currentStart
  const baselineStart = subHours(baselineEnd, 24)
  return {
    baselineStart: baselineStart.toISOString(),
    baselineEnd: baselineEnd.toISOString(),
    currentStart: currentStart.toISOString(),
    currentEnd: currentEnd.toISOString(),
    regressionsOnly: regressionsOnly.value,
    limit: 100,
  }
})

const instanceIdRef = toRef(props, 'instanceId')
const { data, isPending, isError, refetch, isFetching } = useQueryPeriodComparisonQuery(
  instanceIdRef,
  comparisonParams,
)

const rows = computed(() => data.value?.queries ?? [])
const hasRows = computed(() => rows.value.length > 0)

async function refresh() {
  await refetch()
}
</script>

<template>
  <div class="flex h-full min-h-0 flex-col gap-3 p-3">
    <div class="flex flex-wrap items-end justify-between gap-2">
      <div>
        <h1 class="text-base font-semibold tracking-tight">
          {{ t('monitoring.queries.title') }}
          <span v-if="selectedInstance" class="text-muted-foreground">
            — {{ selectedInstance.name }}
          </span>
        </h1>
        <p class="text-xs text-muted-foreground">
          {{ t('monitoring.queries.subtitle') }}
          <span class="text-border"> · </span>
          {{ t('monitoring.queries.rangeLabel') }}
        </p>
      </div>
      <div class="flex flex-wrap items-center gap-3">
        <label class="flex cursor-pointer items-center gap-2 text-xs text-muted-foreground">
          <Checkbox
            :model-value="regressionsOnly"
            @update:model-value="(value) => { regressionsOnly = value === true }"
          />
          {{ t('monitoring.queries.regressionsOnly') }}
        </label>
        <button
          type="button"
          class="rounded-md border border-border px-2 py-1 text-xs text-muted-foreground hover:bg-muted"
          :disabled="isFetching"
          @click="refresh"
        >
          {{ isFetching ? t('monitoring.queries.refreshing') : t('monitoring.queries.refresh') }}
        </button>
      </div>
    </div>

    <div class="flex min-h-0 flex-1 flex-col overflow-hidden rounded-md border border-border bg-background">
      <div v-if="isPending" class="flex flex-1 items-center justify-center text-sm text-muted-foreground">
        {{ t('monitoring.queries.loading') }}
      </div>
      <div v-else-if="isError" class="flex flex-1 items-center justify-center text-sm text-destructive">
        {{ t('monitoring.queries.loadError') }}
      </div>
      <div v-else-if="!hasRows" class="flex flex-1 items-center justify-center px-4 text-center text-sm text-muted-foreground">
        {{
          regressionsOnly
            ? t('monitoring.queries.noRegressions')
            : t('monitoring.queries.noData')
        }}
      </div>
      <div v-else class="min-h-0 flex-1 overflow-auto">
        <Table>
          <TableHeader>
            <TableRow class="hover:bg-transparent">
              <TableHead class="w-[42%]">
                {{ t('monitoring.queries.columns.query') }}
              </TableHead>
              <TableHead class="text-right">
                {{ t('monitoring.queries.columns.calls') }}
              </TableHead>
              <TableHead class="text-right">
                {{ t('monitoring.queries.columns.totalTime') }}
              </TableHead>
              <TableHead class="text-right">
                {{ t('monitoring.queries.columns.avgTime') }}
              </TableHead>
              <TableHead class="text-right">
                {{ t('monitoring.queries.columns.avgDelta') }}
              </TableHead>
              <TableHead class="w-24 text-right">
                {{ t('monitoring.queries.columns.regression') }}
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow
              v-for="row in rows"
              :key="row.queryId"
              :class="cn(row.isRegression && 'bg-destructive/5')"
            >
              <TableCell class="max-w-0 font-mono text-xs">
                <span
                  class="block truncate"
                  :title="row.queryText ?? row.queryId"
                >
                  {{ truncateSql(row.queryText) }}
                </span>
              </TableCell>
              <TableCell class="text-right tabular-nums text-xs">
                {{ formatCalls(row.current?.calls) }}
              </TableCell>
              <TableCell class="text-right tabular-nums text-xs">
                {{ formatMs(row.current?.totalTimeMs) }}
              </TableCell>
              <TableCell class="text-right tabular-nums text-xs">
                {{ formatMs(row.current?.avgTimeMs) }}
              </TableCell>
              <TableCell
                class="text-right tabular-nums text-xs"
                :class="row.isRegression ? 'text-destructive' : 'text-muted-foreground'"
              >
                {{ formatDeltaPct(row.avgTimeMsDeltaPct) }}
              </TableCell>
              <TableCell class="text-right text-xs">
                <span
                  v-if="row.isRegression"
                  class="rounded bg-destructive/15 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-destructive"
                >
                  {{ t('monitoring.queries.regressionBadge') }}
                </span>
                <span v-else class="text-muted-foreground">—</span>
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </div>
    </div>
  </div>
</template>
