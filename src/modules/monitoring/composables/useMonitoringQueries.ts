import { useQuery } from '@tanstack/vue-query'
import { computed, type Ref } from 'vue'
import { useAuthStore } from '@/modules/auth/store/useAuthStore'
import { monitoringApiService } from '@/modules/monitoring/services/monitoringApiService'
import {
  monitoringQueryKeys,
  monitoringRetryFunction,
} from '@/modules/monitoring/utils/queryUtils'
import { config } from '@/shared/config/config'
import type {
  QueryPeriodComparisonParams,
  WaitsTimelineParams,
} from '@/modules/monitoring/types/monitoring.type'

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

export function useQueryPeriodComparisonQuery(
  instanceId: Ref<string>,
  params: Ref<QueryPeriodComparisonParams>,
) {
  const authStore = useAuthStore()

  return useQuery({
    queryKey: computed(() =>
      monitoringQueryKeys.queryPeriodComparison(
        instanceId.value,
        params.value.baselineStart,
        params.value.baselineEnd,
        params.value.currentStart,
        params.value.currentEnd,
        params.value.regressionsOnly ?? false,
        params.value.limit ?? 100,
      ),
    ),
    queryFn: () => monitoringApiService.getQueryPeriodComparison(instanceId.value, params.value),
    enabled: computed(() =>
      config.backend.enabled
      && Boolean(authStore.token)
      && Boolean(instanceId.value),
    ),
    staleTime: 30_000,
    retry: monitoringRetryFunction,
  })
}
