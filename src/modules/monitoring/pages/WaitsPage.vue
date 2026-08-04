<script setup lang="ts">
import DesktopWorkspaceLayout from '@/modules/monitoring/components/DesktopWorkspaceLayout.vue'
import WaitsChartPlaceholder from '@/modules/monitoring/components/WaitsChartPlaceholder.vue'
</script>

<template>
  <DesktopWorkspaceLayout active-tab="waits">
    <WaitsChartPlaceholder />
  </DesktopWorkspaceLayout>
</template>
