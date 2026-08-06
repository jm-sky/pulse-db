<script setup lang="ts">
import DesktopWorkspaceLayout from '@/modules/monitoring/components/DesktopWorkspaceLayout.vue'
import InstanceDetailPanel from '@/modules/monitoring/components/InstanceDetailPanel.vue'

defineProps<{
  instanceId: string
}>()
</script>

<template>
  <DesktopWorkspaceLayout active-tab="instance">
    <InstanceDetailPanel :instance-id="instanceId" />
  </DesktopWorkspaceLayout>
</template>
