<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { cn } from '@/lib/utils'
import { useWorkspaceContext } from '@/modules/monitoring/composables/useWorkspaceContext'
import { MonitoringRoutePaths } from '@/modules/monitoring/routes'

const props = defineProps<{
  activeTab?: 'waits' | 'queries' | null
}>()

const { t } = useI18n()
const router = useRouter()
const { selectedInstanceId } = useWorkspaceContext()

const tabs = computed(() => [
  { id: 'waits' as const, label: t('monitoring.tabs.waits') },
  { id: 'queries' as const, label: t('monitoring.tabs.queries') },
])

function openTab(tab: 'waits' | 'queries') {
  if (!selectedInstanceId.value || tab === props.activeTab) return
  const path = tab === 'waits'
    ? MonitoringRoutePaths.instanceWaits(selectedInstanceId.value)
    : MonitoringRoutePaths.instanceQueries(selectedInstanceId.value)
  void router.push(path)
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
