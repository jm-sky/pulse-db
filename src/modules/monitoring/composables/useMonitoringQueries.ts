import { useQuery } from '@tanstack/vue-query'
import { computed, type Ref } from 'vue'
import { useAuthStore } from '@/modules/auth/store/useAuthStore'
import { monitoringApiService } from '@/modules/monitoring/services/monitoringApiService'
import {
  monitoringQueryKeys,
  monitoringRetryFunction,
} from '@/modules/monitoring/utils/queryUtils'
import { config } from '@/shared/config/config'
import type { WaitsTimelineParams } from '@/modules/monitoring/types/monitoring.type'

export function useMonitoringInstancesQuery() {
  const authStore = useAuthStore()

  return useQuery({
    queryKey: monitoringQueryKeys.instances(),
    queryFn: () => monitoringApiService.listInstances(),
    enabled: computed(() => config.backend.enabled && Boolean(authStore.token)),
    staleTime: 30_000,
    retry: monitoringRetryFunction,
  })
}

export function useWaitsTimelineQuery(
  instanceId: Ref<string>,
  params: Ref<WaitsTimelineParams>,
) {
  const authStore = useAuthStore()

  return useQuery({
    queryKey: computed(() =>
      monitoringQueryKeys.waitsTimeline(
        instanceId.value,
        params.value.start,
        params.value.end,
        params.value.granularity,
      ),
    ),
    queryFn: () => monitoringApiService.getWaitsTimeline(instanceId.value, params.value),
    enabled: computed(() =>
      config.backend.enabled
      && Boolean(authStore.token)
      && Boolean(instanceId.value),
    ),
    staleTime: 30_000,
    retry: monitoringRetryFunction,
  })
}
