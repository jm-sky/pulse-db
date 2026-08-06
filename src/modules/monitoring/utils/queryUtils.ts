import { isAuthError } from '@/shared/utils/errorGuards'

export const monitoringQueryKeys = {
  all: ['monitoring'] as const,
  instances: () => [...monitoringQueryKeys.all, 'instances'] as const,
  waitsTimeline: (instanceId: string, start: string, end: string, granularity?: string) =>
    [...monitoringQueryKeys.all, 'waits-timeline', instanceId, start, end, granularity ?? 'auto'] as const,
  queryPeriodComparison: (
    instanceId: string,
    baselineStart: string,
    baselineEnd: string,
    currentStart: string,
    currentEnd: string,
    regressionsOnly: boolean,
    limit: number,
  ) =>
    [
      ...monitoringQueryKeys.all,
      'query-period-comparison',
      instanceId,
      baselineStart,
      baselineEnd,
      currentStart,
      currentEnd,
      regressionsOnly,
      limit,
    ] as const,
  planChanges: (instanceId: string, since: string) =>
    [...monitoringQueryKeys.all, 'plan-changes', instanceId, since] as const,
  queryPlans: (instanceId: string, queryId: string) =>
    [...monitoringQueryKeys.all, 'query-plans', instanceId, queryId] as const,
  queryPlanDetail: (instanceId: string, queryId: string, planHash: string) =>
    [...monitoringQueryKeys.all, 'query-plan-detail', instanceId, queryId, planHash] as const,
  blocking: (instanceId: string, since: string) =>
    [...monitoringQueryKeys.all, 'blocking', instanceId, since] as const,
  deadlocks: (instanceId: string, since: string) =>
    [...monitoringQueryKeys.all, 'deadlocks', instanceId, since] as const,
  deadlockDetail: (instanceId: string, eventId: string) =>
    [...monitoringQueryKeys.all, 'deadlock-detail', instanceId, eventId] as const,
  indexes: (instanceId: string, snapshotAt?: string | null) =>
    [...monitoringQueryKeys.all, 'indexes', instanceId, snapshotAt ?? 'latest'] as const,
  recommendations: (instanceId: string, status: string, category?: string) =>
    [
      ...monitoringQueryKeys.all,
      'recommendations',
      instanceId,
      status,
      category ?? 'all',
    ] as const,
}

export function monitoringRetryFunction(failureCount: number, error: unknown): boolean {
  if (isAuthError(error)) return false
  if (failureCount >= 2) return false
  const status = (error as { response?: { status?: number } })?.response?.status
  if (status === 403) return false
  return true
}
