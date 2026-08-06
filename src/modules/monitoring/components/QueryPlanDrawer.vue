<script setup lang="ts">
import { computed, ref, toRef, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { toast } from 'vue-sonner'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { copyToClipboard } from '@/lib/copyToClipboard'
import { useQueryPlansQuery } from '@/modules/monitoring/composables/useMonitoringQueries'
import { monitoringApiService } from '@/modules/monitoring/services/monitoringApiService'
import type { QueryPeriodComparisonItem } from '@/modules/monitoring/types/monitoring.type'

const props = defineProps<{
  instanceId: string
  query: QueryPeriodComparisonItem | null
}>()

const open = defineModel<boolean>('open', { default: false })

const { t } = useI18n()
const instanceIdRef = toRef(props, 'instanceId')
const selectedQueryId = computed(() => props.query?.queryId ?? null)
const exportingHash = ref<string | null>(null)

const { data, isPending, isError, refetch, isFetching } = useQueryPlansQuery(
  instanceIdRef,
  selectedQueryId,
)

const plans = computed(() => data.value?.plans ?? [])
const isPlanChange = computed(() => data.value?.isPlanChange ?? false)

watch(open, (isOpen) => {
  if (isOpen && selectedQueryId.value) {
    void refetch()
  }
})

function formatTs(value: string) {
  try {
    return new Date(value).toLocaleString()
  } catch {
    return value
  }
}

async function exportPlan(planHash: string, planFormat: string) {
  if (!props.query) return
  exportingHash.value = planHash
  try {
    const detail = await monitoringApiService.getQueryPlanDetail(
      props.instanceId,
      props.query.queryId,
      planHash,
    )
    const ext = planFormat === 'xml' ? 'xml' : 'json'
    const filename = `plan-${planHash.slice(0, 12)}.${ext}`
    const blob = new Blob([detail.planBody], {
      type: planFormat === 'xml' ? 'application/xml' : 'application/json',
    })
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = filename
    anchor.click()
    URL.revokeObjectURL(url)

    const copied = await copyToClipboard(detail.planBody)
    if (copied === 'copied') {
      toast.success(t('monitoring.queries.plan.copied'))
    }
  } catch {
    toast.error(t('monitoring.queries.plan.exportError'))
  } finally {
    exportingHash.value = null
  }
}
</script>

<template>
  <Sheet v-model:open="open">
    <SheetContent
      side="right"
      class="flex w-full flex-col gap-4 sm:max-w-xl"
    >
      <SheetHeader>
        <SheetTitle>{{ t('monitoring.queries.plan.title') }}</SheetTitle>
        <SheetDescription>
          {{ t('monitoring.queries.plan.subtitle') }}
          <span
            v-if="isPlanChange"
            class="ml-2 inline-flex rounded bg-chart-4/20 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-chart-4"
          >
            {{ t('monitoring.queries.plan.changeBadge') }}
          </span>
        </SheetDescription>
      </SheetHeader>

      <div v-if="query" class="min-h-0 flex-1 space-y-4 overflow-auto px-1 pb-4">
        <div>
          <p class="mb-1 text-xs font-medium text-muted-foreground">
            {{ t('monitoring.queries.plan.queryText') }}
          </p>
          <pre class="max-h-40 overflow-auto rounded-md border border-border bg-muted/40 p-2 font-mono text-xs whitespace-pre-wrap break-all">{{ query.queryText ?? query.queryId }}</pre>
        </div>

        <div>
          <div class="mb-2 flex items-center justify-between gap-2">
            <p class="text-xs font-medium text-muted-foreground">
              {{ t('monitoring.queries.plan.listTitle') }}
            </p>
            <button
              type="button"
              class="rounded-md border border-border px-2 py-1 text-xs text-muted-foreground hover:bg-muted"
              :disabled="isFetching"
              @click="refetch()"
            >
              {{ isFetching ? t('monitoring.queries.refreshing') : t('monitoring.queries.refresh') }}
            </button>
          </div>

          <div
            v-if="isPending"
            class="rounded-md border border-border px-3 py-6 text-center text-sm text-muted-foreground"
          >
            {{ t('monitoring.queries.plan.loading') }}
          </div>
          <div
            v-else-if="isError"
            class="rounded-md border border-border px-3 py-6 text-center text-sm text-destructive"
          >
            {{ t('monitoring.queries.plan.loadError') }}
          </div>
          <div
            v-else-if="plans.length === 0"
            class="rounded-md border border-border px-3 py-6 text-center text-sm text-muted-foreground"
          >
            {{ t('monitoring.queries.plan.noData') }}
          </div>
          <div v-else class="overflow-hidden rounded-md border border-border">
            <Table>
              <TableHeader>
                <TableRow class="hover:bg-transparent">
                  <TableHead>{{ t('monitoring.queries.plan.columns.hash') }}</TableHead>
                  <TableHead>{{ t('monitoring.queries.plan.columns.format') }}</TableHead>
                  <TableHead>{{ t('monitoring.queries.plan.columns.firstSeen') }}</TableHead>
                  <TableHead class="text-right">
                    {{ t('monitoring.queries.plan.columns.actions') }}
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                <TableRow v-for="plan in plans" :key="plan.planHash">
                  <TableCell class="font-mono text-xs" :title="plan.planHash">
                    {{ plan.planHash.slice(0, 12) }}…
                  </TableCell>
                  <TableCell class="text-xs uppercase">
                    {{ plan.planFormat }}
                  </TableCell>
                  <TableCell class="text-xs text-muted-foreground">
                    {{ formatTs(plan.firstSeen) }}
                  </TableCell>
                  <TableCell class="text-right">
                    <button
                      type="button"
                      class="rounded-md border border-border px-2 py-1 text-xs hover:bg-muted"
                      :disabled="exportingHash === plan.planHash"
                      @click="exportPlan(plan.planHash, plan.planFormat)"
                    >
                      {{
                        exportingHash === plan.planHash
                          ? t('monitoring.queries.plan.exporting')
                          : t('monitoring.queries.plan.export')
                      }}
                    </button>
                  </TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </div>
        </div>
      </div>
    </SheetContent>
  </Sheet>
</template>
