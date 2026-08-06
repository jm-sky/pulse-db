<script setup lang="ts">
import DesktopWorkspaceLayout from '@/modules/monitoring/components/DesktopWorkspaceLayout.vue'
import IndexesPanel from '@/modules/monitoring/components/IndexesPanel.vue'

defineProps<{
  instanceId: string
}>()
</script>

<template>
  <DesktopWorkspaceLayout active-tab="indexes">
    <IndexesPanel :instance-id="instanceId" />
  </DesktopWorkspaceLayout>
</template>
