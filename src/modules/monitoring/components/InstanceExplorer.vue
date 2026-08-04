<script setup lang="ts">
import { ChevronDown, ChevronRight, Circle, Database, Server } from 'lucide-vue-next'
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { cn } from '@/lib/utils'
import { useWorkspaceContext } from '@/modules/monitoring/composables/useWorkspaceContext'
import { MonitoringRoutePaths } from '@/modules/monitoring/routes'
import type { MockInstance } from '@/modules/monitoring/mocks/instances'

const { t } = useI18n()
const router = useRouter()
const { instances, selectedInstanceId, selectInstance } = useWorkspaceContext()

const estateOpen = ref(true)
const expanded = ref<Record<string, boolean>>(
  Object.fromEntries(instances.map(i => [i.id, i.id === selectedInstanceId.value])),
)

function toggleInstance(id: string) {
  expanded.value[id] = !expanded.value[id]
}

function openWaits(instance: MockInstance) {
  selectInstance(instance.id)
  expanded.value[instance.id] = true
  void router.push(MonitoringRoutePaths.waits)
}

function statusClass(status: MockInstance['collectorStatus']) {
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
      <span class="rounded bg-muted px-1 py-0.5 text-[10px] text-muted-foreground">
        {{ t('monitoring.explorer.mockHint') }}
      </span>
    </div>

    <div class="flex-1 overflow-y-auto py-1 text-sm">
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
        <div v-for="instance in instances" :key="instance.id" class="mt-0.5">
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
              :class="selectedInstanceId === instance.id && 'bg-sidebar-accent/80'"
              @click="openWaits(instance)"
            >
              {{ t('monitoring.explorer.waits') }}
            </button>
            <button
              type="button"
              disabled
              class="flex w-full items-center rounded-sm px-2 py-0.5 text-left text-muted-foreground opacity-60"
            >
              {{ t('monitoring.explorer.queries') }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </aside>
</template>
