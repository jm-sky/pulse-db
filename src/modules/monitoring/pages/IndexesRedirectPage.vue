<script setup lang="ts">
import { watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { useMonitoringInstancesQuery } from '@/modules/monitoring/composables/useMonitoringQueries'
import { MonitoringRoutePaths } from '@/modules/monitoring/routes'

const { t } = useI18n()
const router = useRouter()
const { data, isSuccess, isError, isPending } = useMonitoringInstancesQuery()

watch(
  [data, isSuccess],
  () => {
    if (!isSuccess.value || !data.value) return
    const active = data.value.instances.filter(instance => instance.isActive)
    const first = active[0] ?? data.value.instances[0]
    if (first) {
      void router.replace(MonitoringRoutePaths.instanceIndexes(first.id))
    }
  },
  { immediate: true },
)
</script>

<template>
  <div class="flex h-dvh items-center justify-center text-sm text-muted-foreground">
    <span v-if="isError">{{ t('monitoring.indexes.loadInstancesError') }}</span>
    <span v-else-if="isPending || !isSuccess || (data?.instances?.length ?? 0) > 0">
      {{ t('monitoring.indexes.loadingInstances') }}
    </span>
    <span v-else>{{ t('monitoring.indexes.noInstances') }}</span>
  </div>
</template>
