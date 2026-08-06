<script setup lang="ts">
import { ChevronDown, ChevronRight, Circle, Database, Server } from 'lucide-vue-next'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { cn } from '@/lib/utils'
import { useWorkspaceContext } from '@/modules/monitoring/composables/useWorkspaceContext'
import { MonitoringRoutePaths } from '@/modules/monitoring/routes'
import type { MonitoredInstance, WorkspaceTab } from '@/modules/monitoring/types/monitoring.type'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const {
  instances,
  selectedInstanceId,
  isInstancesPending,
  isInstancesError,
  isInstancesFetching,
} = useWorkspaceContext()

const estateOpen = ref(true)
const expanded = ref<Record<string, boolean>>({})

watch(
  selectedInstanceId,
  (id) => {
    if (id) expanded.value[id] = true
  },
  { immediate: true },
)

const visibleInstances = computed(() =>
  instances.value.filter(instance => instance.isActive),
)

const activeView = computed<WorkspaceTab>(() => {
  if (route.path.includes('/queries')) return 'queries'
  if (route.path.includes('/indexes')) return 'indexes'
  if (route.path.endsWith('/instance')) return 'instance'
  return 'waits'
})

function toggleInstance(id: string) {
  expanded.value[id] = !expanded.value[id]
}

function openWaits(instance: MonitoredInstance) {
  expanded.value[instance.id] = true
  void router.push(MonitoringRoutePaths.instanceWaits(instance.id))
}

function openQueries(instance: MonitoredInstance) {
  expanded.value[instance.id] = true
  void router.push(MonitoringRoutePaths.instanceQueries(instance.id))
}

function openIndexes(instance: MonitoredInstance) {
  expanded.value[instance.id] = true
  void router.push(MonitoringRoutePaths.instanceIndexes(instance.id))
}

function openInstance(instance: MonitoredInstance) {
  expanded.value[instance.id] = true
  void router.push(MonitoringRoutePaths.instanceDetail(instance.id))
}

function statusClass(status: MonitoredInstance['collectorStatus']) {
  if (status === 'ok') return 'text-success'
  if (status === 'degraded') return 'text-chart-4'
  return 'text-muted-foreground'
}
</script>

<template>
  <aside class="flex h-full w-56 shrink-0 flex-col border-r border-border bg-sidebar text-sidebar-foreground">
    <div class="flex h-8 items-center justify-between border-b border-sidebar-border px-2">
      <span class="text-xs font-medium uppercase tracking-wide text-muted-foreground">
        {{ t('monitoring.explorer.title') }}
      </span>
      <span
        v-if="isInstancesFetching && !isInstancesPending"
        class="rounded bg-muted px-1 py-0.5 text-[10px] text-muted-foreground"
      >
        {{ t('monitoring.explorer.refreshing') }}
      </span>
    </div>

    <div class="flex-1 overflow-y-auto py-1 text-sm">
      <div v-if="isInstancesPending" class="px-2 py-2 text-xs text-muted-foreground">
        {{ t('monitoring.explorer.loading') }}
      </div>
      <div v-else-if="isInstancesError" class="px-2 py-2 text-xs text-destructive">
        {{ t('monitoring.explorer.loadError') }}
      </div>
      <div v-else-if="visibleInstances.length === 0" class="px-2 py-2 text-xs text-muted-foreground">
        {{ t('monitoring.explorer.empty') }}
      </div>

      <template v-else>
        <button
          type="button"
          class="flex w-full items-center gap-1 px-2 py-1 hover:bg-sidebar-accent"
          @click="estateOpen = !estateOpen"
        >
          <ChevronDown v-if="estateOpen" class="size-3.5 shrink-0" />
          <ChevronRight v-else class="size-3.5 shrink-0" />
          <Server class="size-3.5 shrink-0 text-muted-foreground" />
          <span class="font-medium">{{ t('monitoring.explorer.estate') }}</span>
        </button>

        <div v-if="estateOpen" class="ml-2 border-l border-sidebar-border pl-1">
          <div v-for="instance in visibleInstances" :key="instance.id" class="mt-0.5">
            <div class="flex items-center">
              <button
                type="button"
                class="flex size-6 shrink-0 items-center justify-center hover:bg-sidebar-accent"
                @click="toggleInstance(instance.id)"
              >
                <ChevronDown v-if="expanded[instance.id]" class="size-3.5" />
                <ChevronRight v-else class="size-3.5" />
              </button>
              <button
                type="button"
                :class="cn(
                  'flex min-w-0 flex-1 items-center gap-1.5 rounded-sm px-1 py-0.5 text-left hover:bg-sidebar-accent',
                  selectedInstanceId === instance.id && 'bg-sidebar-accent font-medium',
                )"
                @click="openWaits(instance)"
              >
                <Database class="size-3.5 shrink-0 text-muted-foreground" />
                <span class="truncate">{{ instance.name }}</span>
                <Circle
                  class="ml-auto size-2 shrink-0 fill-current"
                  :class="statusClass(instance.collectorStatus)"
                />
              </button>
            </div>

            <div v-if="expanded[instance.id]" class="ml-5 border-l border-sidebar-border pl-1">
              <button
                type="button"
                class="flex w-full items-center rounded-sm px-2 py-0.5 text-left hover:bg-sidebar-accent"
                :class="selectedInstanceId === instance.id && activeView === 'waits' && 'bg-sidebar-accent/80'"
                @click="openWaits(instance)"
              >
                {{ t('monitoring.explorer.waits') }}
              </button>
              <button
                type="button"
                class="flex w-full items-center rounded-sm px-2 py-0.5 text-left hover:bg-sidebar-accent"
                :class="selectedInstanceId === instance.id && activeView === 'queries' && 'bg-sidebar-accent/80'"
                @click="openQueries(instance)"
              >
                {{ t('monitoring.explorer.queries') }}
              </button>
              <button
                type="button"
                class="flex w-full items-center rounded-sm px-2 py-0.5 text-left hover:bg-sidebar-accent"
                :class="selectedInstanceId === instance.id && activeView === 'indexes' && 'bg-sidebar-accent/80'"
                @click="openIndexes(instance)"
              >
                {{ t('monitoring.explorer.indexes') }}
              </button>
              <button
                type="button"
                class="flex w-full items-center rounded-sm px-2 py-0.5 text-left hover:bg-sidebar-accent"
                :class="selectedInstanceId === instance.id && activeView === 'instance' && 'bg-sidebar-accent/80'"
                @click="openInstance(instance)"
              >
                {{ t('monitoring.explorer.instance') }}
              </button>
            </div>
          </div>
        </div>
      </template>
    </div>
  </aside>
</template>
