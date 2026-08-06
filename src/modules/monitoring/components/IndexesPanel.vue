<script setup lang="ts">
import { computed, toRef } from 'vue'
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
  useIndexesQuery,
  useRecommendationsQuery,
} from '@/modules/monitoring/composables/useMonitoringQueries'
import { useWorkspaceContext } from '@/modules/monitoring/composables/useWorkspaceContext'

const props = defineProps<{
  instanceId: string
}>()

const { t } = useI18n()
const { selectedInstance } = useWorkspaceContext()

const instanceIdRef = toRef(props, 'instanceId')
const recParams = computed(() => ({ status: 'open' as const }))

const {
  data: indexesData,
  isPending: indexesPending,
  isError: indexesError,
  refetch: refetchIndexes,
  isFetching: indexesFetching,
} = useIndexesQuery(instanceIdRef)

const {
  data: recsData,
  isPending: recsPending,
  isError: recsError,
  refetch: refetchRecs,
  isFetching: recsFetching,
} = useRecommendationsQuery(instanceIdRef, recParams)

const indexes = computed(() => indexesData.value?.indexes ?? [])
const recommendations = computed(() => recsData.value?.recommendations ?? [])
const isPostgresql = computed(() => selectedInstance.value?.engine === 'postgresql')
const unusedRecs = computed(() =>
  recommendations.value.filter(r => r.category === 'unused_index'),
)
const missingRecs = computed(() =>
  recommendations.value.filter(r => r.category === 'missing_index'),
)

const isFetching = computed(() => indexesFetching.value || recsFetching.value)
const isPending = computed(() => indexesPending.value || recsPending.value)

async function refresh() {
  await Promise.all([refetchIndexes(), refetchRecs()])
}

function formatBytes(value: number | null) {
  if (value == null) return '—'
  if (value < 1024) return `${value} B`
  if (value < 1024 ** 2) return `${(value / 1024).toFixed(1)} KB`
  if (value < 1024 ** 3) return `${(value / 1024 ** 2).toFixed(1)} MB`
  return `${(value / 1024 ** 3).toFixed(1)} GB`
}

function formatRatio(value: number | null) {
  if (value == null) return '—'
  return `${(value * 100).toFixed(1)}%`
}

function evidencePreview(evidence: Record<string, unknown>) {
  try {
    return JSON.stringify(evidence)
  } catch {
    return String(evidence)
  }
}

async function copyDdl(ddl: string | null) {
  if (!ddl) return
  const result = await copyToClipboard(ddl)
  if (result === 'copied') {
    toast.success(t('monitoring.indexes.ddlCopied'))
  } else {
    toast.error(t('monitoring.indexes.ddlCopyFailed'))
  }
}
</script>

<template>
  <div class="flex h-full min-h-0 flex-col gap-3 p-3">
    <div class="flex flex-wrap items-end justify-between gap-2">
      <div>
        <h1 class="text-base font-semibold tracking-tight">
          {{ t('monitoring.indexes.title') }}
          <span v-if="selectedInstance" class="text-muted-foreground">
            — {{ selectedInstance.name }}
          </span>
        </h1>
        <p class="text-xs text-muted-foreground">
          {{ t('monitoring.indexes.subtitle') }}
          <template v-if="indexesData?.snapshotAt">
            <span class="text-border"> · </span>
            {{ t('monitoring.indexes.snapshotAt') }}
            {{ new Date(indexesData.snapshotAt).toLocaleString() }}
          </template>
        </p>
      </div>
      <button
        type="button"
        class="rounded-md border border-border px-2 py-1 text-xs text-muted-foreground hover:bg-muted"
        :disabled="isFetching"
        @click="refresh"
      >
        {{ isFetching ? t('monitoring.indexes.refreshing') : t('monitoring.indexes.refresh') }}
      </button>
    </div>

    <div class="flex min-h-0 flex-1 flex-col gap-3 overflow-auto">
      <section class="flex min-h-0 flex-col overflow-hidden rounded-md border border-border bg-background">
        <div class="border-b border-border px-3 py-2 text-xs font-medium">
          {{ t('monitoring.indexes.inventoryTitle') }}
        </div>
        <div v-if="isPending" class="px-3 py-8 text-center text-sm text-muted-foreground">
          {{ t('monitoring.indexes.loading') }}
        </div>
        <div v-else-if="indexesError" class="px-3 py-8 text-center text-sm text-destructive">
          {{ t('monitoring.indexes.loadError') }}
        </div>
        <div v-else-if="indexes.length === 0" class="px-3 py-8 text-center text-sm text-muted-foreground">
          {{ t('monitoring.indexes.noInventory') }}
        </div>
        <div v-else class="min-h-0 max-h-[45vh] overflow-auto">
          <Table>
            <TableHeader>
              <TableRow class="hover:bg-transparent">
                <TableHead>{{ t('monitoring.indexes.columns.object') }}</TableHead>
                <TableHead class="text-right">
                  {{ t('monitoring.indexes.columns.size') }}
                </TableHead>
                <TableHead class="text-right">
                  {{ t('monitoring.indexes.columns.scans') }}
                </TableHead>
                <TableHead class="text-right">
                  {{ t('monitoring.indexes.columns.bloat') }}
                </TableHead>
                <TableHead class="text-right">
                  {{ t('monitoring.indexes.columns.unused') }}
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow v-for="idx in indexes" :key="idx.id">
                <TableCell class="font-mono text-xs">
                  <div class="truncate" :title="`${idx.databaseName}.${idx.schemaName}.${idx.tableName}.${idx.indexName}`">
                    {{ idx.schemaName }}.{{ idx.tableName }}.{{ idx.indexName }}
                  </div>
                  <div class="text-[10px] text-muted-foreground">
                    {{ idx.databaseName }}
                  </div>
                </TableCell>
                <TableCell class="text-right tabular-nums text-xs">
                  {{ formatBytes(idx.sizeBytes) }}
                </TableCell>
                <TableCell class="text-right tabular-nums text-xs">
                  {{ idx.scans ?? '—' }}
                </TableCell>
                <TableCell class="text-right tabular-nums text-xs">
                  {{ formatRatio(idx.bloatRatio) }}
                </TableCell>
                <TableCell class="text-right text-xs">
                  <span
                    v-if="idx.isUnused"
                    class="rounded bg-chart-4/20 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-chart-4"
                  >
                    {{ t('monitoring.indexes.unusedBadge') }}
                  </span>
                  <span v-else class="text-muted-foreground">—</span>
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </div>
      </section>

      <section class="overflow-hidden rounded-md border border-border bg-background">
        <div class="border-b border-border px-3 py-2 text-xs font-medium">
          {{ t('monitoring.indexes.recommendationsTitle') }}
        </div>
        <div v-if="recsPending" class="px-3 py-6 text-center text-sm text-muted-foreground">
          {{ t('monitoring.indexes.loadingRecs') }}
        </div>
        <div v-else-if="recsError" class="px-3 py-6 text-center text-sm text-destructive">
          {{ t('monitoring.indexes.loadRecsError') }}
        </div>
        <div v-else class="divide-y divide-border">
          <div class="px-3 py-2">
            <p class="mb-2 text-xs font-medium text-muted-foreground">
              {{ t('monitoring.indexes.unusedTitle') }}
            </p>
            <div v-if="unusedRecs.length === 0" class="text-sm text-muted-foreground">
              {{ t('monitoring.indexes.noUnusedRecs') }}
            </div>
            <ul v-else class="space-y-2">
              <li
                v-for="rec in unusedRecs"
                :key="rec.id"
                class="rounded-md border border-border p-2"
              >
                <div class="mb-1 flex items-start justify-between gap-2">
                  <span class="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                    {{ rec.category }}
                  </span>
                  <button
                    v-if="rec.ddlSuggestion"
                    type="button"
                    class="rounded-md border border-border px-2 py-0.5 text-xs hover:bg-muted"
                    @click="copyDdl(rec.ddlSuggestion)"
                  >
                    {{ t('monitoring.indexes.copyDdl') }}
                  </button>
                </div>
                <pre
                  v-if="rec.ddlSuggestion"
                  class="mb-1 overflow-auto rounded bg-muted/40 p-2 font-mono text-xs whitespace-pre-wrap"
                >{{ rec.ddlSuggestion }}</pre>
                <p class="truncate text-[11px] text-muted-foreground" :title="evidencePreview(rec.evidence)">
                  {{ evidencePreview(rec.evidence) }}
                </p>
              </li>
            </ul>
          </div>

          <div class="px-3 py-2">
            <p class="mb-2 text-xs font-medium text-muted-foreground">
              {{ t('monitoring.indexes.missingTitle') }}
            </p>
            <div v-if="isPostgresql" class="text-sm text-muted-foreground">
              {{ t('monitoring.indexes.missingNotOnPg') }}
            </div>
            <div v-else-if="missingRecs.length === 0" class="text-sm text-muted-foreground">
              {{ t('monitoring.indexes.noMissingRecs') }}
            </div>
            <ul v-else class="space-y-2">
              <li
                v-for="rec in missingRecs"
                :key="rec.id"
                class="rounded-md border border-border p-2"
              >
                <div class="mb-1 flex items-start justify-between gap-2">
                  <span class="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                    {{ rec.category }}
                  </span>
                  <button
                    v-if="rec.ddlSuggestion"
                    type="button"
                    class="rounded-md border border-border px-2 py-0.5 text-xs hover:bg-muted"
                    @click="copyDdl(rec.ddlSuggestion)"
                  >
                    {{ t('monitoring.indexes.copyDdl') }}
                  </button>
                </div>
                <pre
                  v-if="rec.ddlSuggestion"
                  class="mb-1 overflow-auto rounded bg-muted/40 p-2 font-mono text-xs whitespace-pre-wrap"
                >{{ rec.ddlSuggestion }}</pre>
                <p class="truncate text-[11px] text-muted-foreground" :title="evidencePreview(rec.evidence)">
                  {{ evidencePreview(rec.evidence) }}
                </p>
              </li>
            </ul>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>
