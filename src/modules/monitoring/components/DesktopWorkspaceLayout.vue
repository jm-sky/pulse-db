<script setup lang="ts">
import { ref } from 'vue'
import DesktopCommandPalette from '@/modules/monitoring/components/DesktopCommandPalette.vue'
import DesktopMenuBar from '@/modules/monitoring/components/DesktopMenuBar.vue'
import DesktopStatusBar from '@/modules/monitoring/components/DesktopStatusBar.vue'
import InstanceExplorer from '@/modules/monitoring/components/InstanceExplorer.vue'
import WorkspaceTabBar from '@/modules/monitoring/components/WorkspaceTabBar.vue'

withDefaults(
  defineProps<{
    activeTab?: 'waits'
  }>(),
  { activeTab: 'waits' },
)

const explorerOpen = ref(true)
const commandOpen = ref(false)
</script>

<template>
  <div class="flex h-dvh min-h-0 flex-col overflow-hidden bg-background text-foreground">
    <DesktopMenuBar
      v-model:explorer-open="explorerOpen"
      @open-command-palette="commandOpen = true"
    />

    <div class="flex min-h-0 flex-1">
      <InstanceExplorer v-show="explorerOpen" />

      <div class="flex min-w-0 flex-1 flex-col">
        <WorkspaceTabBar :active-tab="activeTab" />
        <main class="min-h-0 flex-1 overflow-auto bg-background">
          <slot />
        </main>
      </div>
    </div>

    <DesktopStatusBar />
    <DesktopCommandPalette v-model:open="commandOpen" />
  </div>
</template>
