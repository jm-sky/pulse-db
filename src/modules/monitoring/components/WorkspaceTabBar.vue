<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { cn } from '@/lib/utils'
import { useWorkspaceContext } from '@/modules/monitoring/composables/useWorkspaceContext'
import { MonitoringRoutePaths } from '@/modules/monitoring/routes'
import type { WorkspaceTab } from '@/modules/monitoring/types/monitoring.type'

const props = defineProps<{
  activeTab?: WorkspaceTab | null
}>()

const { t } = useI18n()
const router = useRouter()
const { selectedInstanceId } = useWorkspaceContext()

const tabs = computed(() => [
  { id: 'waits' as const, label: t('monitoring.tabs.waits') },
  { id: 'queries' as const, label: t('monitoring.tabs.queries') },
  { id: 'indexes' as const, label: t('monitoring.tabs.indexes') },
  { id: 'instance' as const, label: t('monitoring.tabs.instance') },
])

function pathForTab(tab: WorkspaceTab, instanceId: string) {
  const paths: Record<WorkspaceTab, string> = {
    indexes: MonitoringRoutePaths.instanceIndexes(instanceId),
    instance: MonitoringRoutePaths.instanceDetail(instanceId),
    queries: MonitoringRoutePaths.instanceQueries(instanceId),
    waits: MonitoringRoutePaths.instanceWaits(instanceId),
  }
  return paths[tab]
}

function openTab(tab: WorkspaceTab) {
  if (!selectedInstanceId.value || tab === props.activeTab) return
  void router.push(pathForTab(tab, selectedInstanceId.value))
}
</script>

<template>
  <div class="flex h-8 shrink-0 items-end gap-0 border-b border-border bg-muted/40 px-1">
    <button
      v-for="tab in tabs"
      :key="tab.id"
      type="button"
      :class="cn(
        'relative flex h-7 items-center border border-b-0 border-transparent px-3 text-xs',
        'rounded-t-md text-muted-foreground hover:text-foreground',
        activeTab === tab.id
          && 'border-border bg-background text-foreground',
      )"
      @click="openTab(tab.id)"
    >
      {{ tab.label }}
    </button>
  </div>
</template>
