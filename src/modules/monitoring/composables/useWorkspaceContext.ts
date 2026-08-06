import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { useMonitoringInstancesQuery } from '@/modules/monitoring/composables/useMonitoringQueries'
import type { MonitoredInstance } from '@/modules/monitoring/types/monitoring.type'

export function useWorkspaceContext() {
  const route = useRoute()
  const { t } = useI18n()
  const {
    data: instancesData,
    isPending: isInstancesPending,
    isError: isInstancesError,
    isFetching: isInstancesFetching,
  } = useMonitoringInstancesQuery()

  const timeRangeLabel = computed(() => t('monitoring.status.lastOneHour'))

  const routeInstanceId = computed(() => {
    const id = route.params.instanceId
    return typeof id === 'string' ? id : undefined
  })

  const instances = computed(() => instancesData.value?.instances ?? [])

  const selectedInstanceId = computed(() => {
    if (routeInstanceId.value) return routeInstanceId.value
    const active = instances.value.find(instance => instance.isActive)
    return active?.id ?? instances.value[0]?.id ?? ''
  })

  const selectedInstance = computed<MonitoredInstance | undefined>(() =>
    instances.value.find(instance => instance.id === selectedInstanceId.value),
  )

  return {
    instances,
    isInstancesPending,
    isInstancesError,
    isInstancesFetching,
    selectedInstanceId,
    selectedInstance,
    timeRangeLabel,
    routeInstanceId,
  }
}
