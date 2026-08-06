<script setup lang="ts">
import { subHours } from 'date-fns'
import { computed, ref, toRef } from 'vue'
import { useI18n } from 'vue-i18n'
import { toast } from 'vue-sonner'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { copyToClipboard } from '@/lib/copyToClipboard'
import {
  useBlockingEventsQuery,
  useDeadlockEventsQuery,
} from '@/modules/monitoring/composables/useMonitoringQueries'
import { useWorkspaceContext } from '@/modules/monitoring/composables/useWorkspaceContext'
import { monitoringApiService } from '@/modules/monitoring/services/monitoringApiService'
import { formatMs } from '@/modules/monitoring/utils/formatQueryMetrics'

const props = defineProps<{
  instanceId: string
}>()

const { t } = useI18n()
const { selectedInstance } = useWorkspaceContext()

const since = computed(() => subHours(new Date(), 24).toISOString())
const instanceIdRef = toRef(props, 'instanceId')
const exportingId = ref<string | null>(null)

const isPostgresql = computed(() => selectedInstance.value?.engine === 'postgresql')

const {
  data: blockingData,
  isPending: blockingPending,
  isError: blockingError,
  refetch: refetchBlocking,
  isFetching: blockingFetching,
} = useBlockingEventsQuery(instanceIdRef, since)

const {
  data: deadlockData,
  isPending: deadlockPending,
  isError: deadlockError,
  refetch: refetchDeadlocks,
  isFetching: deadlockFetching,
} = useDeadlockEventsQuery(instanceIdRef, since)

const blockingEvents = computed(() => blockingData.value?.events ?? [])
const deadlockEvents = computed(() => deadlockData.value?.events ?? [])
const isFetching = computed(() => blockingFetching.value || deadlockFetching.value)

async function refresh() {
  await Promise.all([refetchBlocking(), refetchDeadlocks()])
}

function formatTs(value: string) {
  try {
    return new Date(value).toLocaleString()
  } catch {
    return value
  }
}

function detailsPreview(details: Record<string, unknown>) {
  try {
    return JSON.stringify(details)
  } catch {
    return String(details)
  }
}

async function exportDeadlockXml(eventId: string) {
  exportingId.value = eventId
  try {
    const detail = await monitoringApiService.getDeadlockDetail(props.instanceId, eventId)
    const xml
      = typeof detail.details.xml === 'string'
        ? detail.details.xml
        : typeof detail.details.deadlock_xml === 'string'
          ? detail.details.deadlock_xml
          : JSON.stringify(detail.details, null, 2)
    const blob = new Blob([xml], { type: 'application/xml' })
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `deadlock-${eventId.slice(0, 8)}.xml`
    anchor.click()
    URL.revokeObjectURL(url)
    const copied = await copyToClipboard(xml)
    if (copied === 'copied') {
      toast.success(t('monitoring.instance.deadlockCopied'))
    }
  } catch {
    toast.error(t('monitoring.instance.deadlockExportError'))
  } finally {
    exportingId.value = null
  }
}
</script>

<template>
  <div class="flex h-full min-h-0 flex-col gap-3 p-3">
    <div class="flex flex-wrap items-end justify-between gap-2">
      <div>
        <h1 class="text-base font-semibold tracking-tight">
          {{ t('monitoring.instance.title') }}
          <span v-if="selectedInstance" class="text-muted-foreground">
            — {{ selectedInstance.name }}
          </span>
        </h1>
        <p class="text-xs text-muted-foreground">
          {{ t('monitoring.instance.subtitle') }}
          <span class="text-border"> · </span>
          {{ t('monitoring.instance.rangeLabel') }}
        </p>
      </div>
      <button
        type="button"
        class="rounded-md border border-border px-2 py-1 text-xs text-muted-foreground hover:bg-muted"
        :disabled="isFetching"
        @click="refresh"
      >
        {{ isFetching ? t('monitoring.instance.refreshing') : t('monitoring.instance.refresh') }}
      </button>
    </div>

    <section
      v-if="selectedInstance"
      class="grid gap-2 rounded-md border border-border bg-background p-3 text-xs sm:grid-cols-2 lg:grid-cols-4"
    >
      <div>
        <div class="text-muted-foreground">
          {{ t('monitoring.instance.fields.engine') }}
        </div>
        <div class="font-medium">
          {{ t(`monitoring.status.engine.${selectedInstance.engine}`) }}
        </div>
      </div>
      <div>
        <div class="text-muted-foreground">
          {{ t('monitoring.instance.fields.endpoint') }}
        </div>
        <div class="font-mono font-medium">
          {{ selectedInstance.host }}:{{ selectedInstance.port }}
        </div>
      </div>
      <div>
        <div class="text-muted-foreground">
          {{ t('monitoring.instance.fields.collector') }}
        </div>
        <div class="font-medium">
          {{ t(`monitoring.status.collector${selectedInstance.collectorStatus === 'ok' ? 'Ok' : selectedInstance.collectorStatus === 'degraded' ? 'Degraded' : 'Unknown'}`) }}
        </div>
      </div>
      <div>
        <div class="text-muted-foreground">
          {{ t('monitoring.instance.fields.lastSample') }}
        </div>
        <div class="font-medium">
          {{
            selectedInstance.lastSampleAt
              ? formatTs(selectedInstance.lastSampleAt)
              : '—'
          }}
        </div>
      </div>
    </section>

    <div class="flex min-h-0 flex-1 flex-col gap-3 overflow-auto">
      <section class="overflow-hidden rounded-md border border-border bg-background">
        <div class="border-b border-border px-3 py-2 text-xs font-medium">
          {{ t('monitoring.instance.blockingTitle') }}
        </div>
        <div v-if="blockingPending" class="px-3 py-8 text-center text-sm text-muted-foreground">
          {{ t('monitoring.instance.loadingBlocking') }}
        </div>
        <div v-else-if="blockingError" class="px-3 py-8 text-center text-sm text-destructive">
          {{ t('monitoring.instance.loadBlockingError') }}
        </div>
        <div v-else-if="blockingEvents.length === 0" class="px-3 py-8 text-center text-sm text-muted-foreground">
          {{ t('monitoring.instance.noBlocking') }}
        </div>
        <div v-else class="max-h-[40vh] overflow-auto">
          <Table>
            <TableHeader>
              <TableRow class="hover:bg-transparent">
                <TableHead>{{ t('monitoring.instance.columns.detectedAt') }}</TableHead>
                <TableHead>{{ t('monitoring.instance.columns.blockingQuery') }}</TableHead>
                <TableHead>{{ t('monitoring.instance.columns.blockedQuery') }}</TableHead>
                <TableHead class="text-right">
                  {{ t('monitoring.instance.columns.duration') }}
                </TableHead>
                <TableHead>{{ t('monitoring.instance.columns.details') }}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow v-for="event in blockingEvents" :key="event.id">
                <TableCell class="whitespace-nowrap text-xs text-muted-foreground">
                  {{ formatTs(event.detectedAt) }}
                </TableCell>
                <TableCell class="max-w-[8rem] truncate font-mono text-xs" :title="event.blockingQueryId ?? undefined">
                  {{ event.blockingQueryId?.slice(0, 8) ?? '—' }}
                </TableCell>
                <TableCell class="max-w-[8rem] truncate font-mono text-xs" :title="event.blockedQueryId ?? undefined">
                  {{ event.blockedQueryId?.slice(0, 8) ?? '—' }}
                </TableCell>
                <TableCell class="text-right tabular-nums text-xs">
                  {{ formatMs(event.blockedDurationMs) }}
                </TableCell>
                <TableCell class="max-w-[14rem] truncate font-mono text-[11px] text-muted-foreground" :title="detailsPreview(event.details)">
                  {{ detailsPreview(event.details) }}
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </div>
      </section>

      <section class="overflow-hidden rounded-md border border-border bg-background">
        <div class="border-b border-border px-3 py-2 text-xs font-medium">
          {{ t('monitoring.instance.deadlocksTitle') }}
        </div>
        <div v-if="isPostgresql" class="px-3 py-8 text-center text-sm text-muted-foreground">
          {{ t('monitoring.instance.deadlocksNotOnPg') }}
        </div>
        <div v-else-if="deadlockPending" class="px-3 py-8 text-center text-sm text-muted-foreground">
          {{ t('monitoring.instance.loadingDeadlocks') }}
        </div>
        <div v-else-if="deadlockError" class="px-3 py-8 text-center text-sm text-destructive">
          {{ t('monitoring.instance.loadDeadlocksError') }}
        </div>
        <div v-else-if="deadlockEvents.length === 0" class="px-3 py-8 text-center text-sm text-muted-foreground">
          {{ t('monitoring.instance.noDeadlocks') }}
        </div>
        <div v-else class="max-h-[40vh] overflow-auto">
          <Table>
            <TableHeader>
              <TableRow class="hover:bg-transparent">
                <TableHead>{{ t('monitoring.instance.columns.detectedAt') }}</TableHead>
                <TableHead>{{ t('monitoring.instance.columns.victimQuery') }}</TableHead>
                <TableHead>{{ t('monitoring.instance.columns.victimProcess') }}</TableHead>
                <TableHead class="text-right">
                  {{ t('monitoring.instance.columns.actions') }}
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow v-for="event in deadlockEvents" :key="event.id">
                <TableCell class="whitespace-nowrap text-xs text-muted-foreground">
                  {{ formatTs(event.detectedAt) }}
                </TableCell>
                <TableCell class="font-mono text-xs" :title="event.victimQueryId ?? undefined">
                  {{ event.victimQueryId?.slice(0, 8) ?? '—' }}
                </TableCell>
                <TableCell class="font-mono text-xs">
                  {{ event.victimProcessId ?? '—' }}
                </TableCell>
                <TableCell class="text-right">
                  <button
                    v-if="event.hasXml"
                    type="button"
                    class="rounded-md border border-border px-2 py-1 text-xs hover:bg-muted"
                    :disabled="exportingId === event.id"
                    @click="exportDeadlockXml(event.id)"
                  >
                    {{
                      exportingId === event.id
                        ? t('monitoring.instance.exporting')
                        : t('monitoring.instance.exportXml')
                    }}
                  </button>
                  <span v-else class="text-xs text-muted-foreground">—</span>
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </div>
      </section>
    </div>
  </div>
</template>
