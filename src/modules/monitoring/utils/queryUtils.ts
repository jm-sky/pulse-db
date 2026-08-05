import { isAuthError } from '@/shared/utils/errorGuards'

export const monitoringQueryKeys = {
  all: ['monitoring'] as const,
  instances: () => [...monitoringQueryKeys.all, 'instances'] as const,
  waitsTimeline: (instanceId: string, start: string, end: string, granularity?: string) =>
    [...monitoringQueryKeys.all, 'waits-timeline', instanceId, start, end, granularity ?? 'auto'] as const,
}

export function monitoringRetryFunction(failureCount: number, error: unknown): boolean {
  if (isAuthError(error)) return false
  if (failureCount >= 2) return false
  const status = (error as { response?: { status?: number } })?.response?.status
  if (status === 403) return false
  return true
}
