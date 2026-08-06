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
  RecommendationsParams,
  WaitsTimelineParams,
} from '@/modules/monitoring/types/monitoring.type'

function useMonitoringEnabled(instanceId?: Ref<string>) {
  const authStore = useAuthStore()
  return computed(() =>
    config.backend.enabled
    && Boolean(authStore.token)
    && (instanceId ? Boolean(instanceId.value) : true),
  )
}

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
    enabled: useMonitoringEnabled(instanceId),
    staleTime: 30_000,
    retry: monitoringRetryFunction,
  })
}

export function useQueryPeriodComparisonQuery(
  instanceId: Ref<string>,
  params: Ref<QueryPeriodComparisonParams>,
) {
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
    enabled: useMonitoringEnabled(instanceId),
    staleTime: 30_000,
    retry: monitoringRetryFunction,
  })
}

export function usePlanChangesQuery(instanceId: Ref<string>, since: Ref<string>) {
  return useQuery({
    queryKey: computed(() =>
      monitoringQueryKeys.planChanges(instanceId.value, since.value),
    ),
    queryFn: () => monitoringApiService.getPlanChanges(instanceId.value, since.value),
    enabled: useMonitoringEnabled(instanceId),
    staleTime: 30_000,
    retry: monitoringRetryFunction,
  })
}

export function useQueryPlansQuery(
  instanceId: Ref<string>,
  queryId: Ref<string | null>,
) {
  const authStore = useAuthStore()

  return useQuery({
    queryKey: computed(() =>
      monitoringQueryKeys.queryPlans(instanceId.value, queryId.value ?? ''),
    ),
    queryFn: () => monitoringApiService.listQueryPlans(instanceId.value, queryId.value!),
    enabled: computed(() =>
      config.backend.enabled
      && Boolean(authStore.token)
      && Boolean(instanceId.value)
      && Boolean(queryId.value),
    ),
    staleTime: 30_000,
    retry: monitoringRetryFunction,
  })
}

export function useBlockingEventsQuery(instanceId: Ref<string>, since: Ref<string>) {
  return useQuery({
    queryKey: computed(() =>
      monitoringQueryKeys.blocking(instanceId.value, since.value),
    ),
    queryFn: () => monitoringApiService.getBlockingEvents(instanceId.value, since.value),
    enabled: useMonitoringEnabled(instanceId),
    staleTime: 30_000,
    retry: monitoringRetryFunction,
  })
}

export function useDeadlockEventsQuery(instanceId: Ref<string>, since: Ref<string>) {
  return useQuery({
    queryKey: computed(() =>
      monitoringQueryKeys.deadlocks(instanceId.value, since.value),
    ),
    queryFn: () => monitoringApiService.getDeadlockEvents(instanceId.value, since.value),
    enabled: useMonitoringEnabled(instanceId),
    staleTime: 30_000,
    retry: monitoringRetryFunction,
  })
}

export function useIndexesQuery(instanceId: Ref<string>) {
  return useQuery({
    queryKey: computed(() => monitoringQueryKeys.indexes(instanceId.value)),
    queryFn: () => monitoringApiService.getIndexes(instanceId.value),
    enabled: useMonitoringEnabled(instanceId),
    staleTime: 30_000,
    retry: monitoringRetryFunction,
  })
}

export function useRecommendationsQuery(
  instanceId: Ref<string>,
  params: Ref<RecommendationsParams>,
) {
  return useQuery({
    queryKey: computed(() =>
      monitoringQueryKeys.recommendations(
        instanceId.value,
        params.value.status ?? 'open',
        params.value.category,
      ),
    ),
    queryFn: () => monitoringApiService.getRecommendations(instanceId.value, params.value),
    enabled: useMonitoringEnabled(instanceId),
    staleTime: 30_000,
    retry: monitoringRetryFunction,
  })
}
