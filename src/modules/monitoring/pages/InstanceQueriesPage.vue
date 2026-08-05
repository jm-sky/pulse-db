<script setup lang="ts">
import DesktopWorkspaceLayout from '@/modules/monitoring/components/DesktopWorkspaceLayout.vue'
import QueriesTable from '@/modules/monitoring/components/QueriesTable.vue'

defineProps<{
  instanceId: string
}>()
</script>

<template>
  <DesktopWorkspaceLayout active-tab="queries">
    <QueriesTable :instance-id="instanceId" />
  </DesktopWorkspaceLayout>
</template>
