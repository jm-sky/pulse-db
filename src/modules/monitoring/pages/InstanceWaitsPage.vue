<script setup lang="ts">
import DesktopWorkspaceLayout from '@/modules/monitoring/components/DesktopWorkspaceLayout.vue'
import WaitsChart from '@/modules/monitoring/components/WaitsChart.vue'

defineProps<{
  instanceId: string
}>()
</script>

<template>
  <DesktopWorkspaceLayout active-tab="waits">
    <WaitsChart :instance-id="instanceId" />
  </DesktopWorkspaceLayout>
</template>
