import { apiClient } from '@/shared/services/apiClient'
import type {
  BlockingEvents,
  DeadlockEventDetail,
  DeadlockEvents,
  IndexesResponse,
  MonitoredInstanceList,
  PlanChanges,
  QueryPeriodComparison,
  QueryPeriodComparisonParams,
  QueryPlanDetail,
  QueryPlansList,
  RecommendationsParams,
  RecommendationsResponse,
  WaitsTimeline,
  WaitsTimelineParams,
} from '@/modules/monitoring/types/monitoring.type'

class MonitoringApiService {
  async listInstances(): Promise<MonitoredInstanceList> {
    const response = await apiClient.get<MonitoredInstanceList>('/monitoring/instances')
    return response.data
  }

  async getWaitsTimeline(instanceId: string, params: WaitsTimelineParams): Promise<WaitsTimeline> {
    const response = await apiClient.get<WaitsTimeline>(
      `/monitoring/instances/${instanceId}/waits/timeline`,
      { params },
    )
    return response.data
  }

  async getQueryPeriodComparison(
    instanceId: string,
    params: QueryPeriodComparisonParams,
  ): Promise<QueryPeriodComparison> {
    const response = await apiClient.get<QueryPeriodComparison>(
      `/monitoring/instances/${instanceId}/queries/period-comparison`,
      {
        params: {
          baseline_start: params.baselineStart,
          baseline_end: params.baselineEnd,
          current_start: params.currentStart,
          current_end: params.currentEnd,
          regressions_only: params.regressionsOnly ?? false,
          limit: params.limit ?? 100,
        },
      },
    )
    return response.data
  }

  async getPlanChanges(instanceId: string, since: string): Promise<PlanChanges> {
    const response = await apiClient.get<PlanChanges>(
      `/monitoring/instances/${instanceId}/queries/plan-changes`,
      { params: { since } },
    )
    return response.data
  }

  async listQueryPlans(instanceId: string, queryId: string): Promise<QueryPlansList> {
    const response = await apiClient.get<QueryPlansList>(
      `/monitoring/instances/${instanceId}/queries/${queryId}/plans`,
    )
    return response.data
  }

  async getQueryPlanDetail(
    instanceId: string,
    queryId: string,
    planHash: string,
  ): Promise<QueryPlanDetail> {
    const response = await apiClient.get<QueryPlanDetail>(
      `/monitoring/instances/${instanceId}/queries/${queryId}/plans/${planHash}`,
    )
    return response.data
  }

  async getBlockingEvents(instanceId: string, since: string): Promise<BlockingEvents> {
    const response = await apiClient.get<BlockingEvents>(
      `/monitoring/instances/${instanceId}/blocking`,
      { params: { since } },
    )
    return response.data
  }

  async getDeadlockEvents(instanceId: string, since: string): Promise<DeadlockEvents> {
    const response = await apiClient.get<DeadlockEvents>(
      `/monitoring/instances/${instanceId}/deadlocks`,
      { params: { since } },
    )
    return response.data
  }

  async getDeadlockDetail(instanceId: string, eventId: string): Promise<DeadlockEventDetail> {
    const response = await apiClient.get<DeadlockEventDetail>(
      `/monitoring/instances/${instanceId}/deadlocks/${eventId}`,
    )
    return response.data
  }

  async getIndexes(instanceId: string, snapshotAt?: string): Promise<IndexesResponse> {
    const response = await apiClient.get<IndexesResponse>(
      `/monitoring/instances/${instanceId}/indexes`,
      { params: snapshotAt ? { snapshot_at: snapshotAt } : undefined },
    )
    return response.data
  }

  async getRecommendations(
    instanceId: string,
    params: RecommendationsParams = {},
  ): Promise<RecommendationsResponse> {
    const response = await apiClient.get<RecommendationsResponse>(
      `/monitoring/instances/${instanceId}/recommendations`,
      {
        params: {
          ...(params.category ? { category: params.category } : {}),
          ...(params.status === null
            ? {}
            : { status: params.status ?? 'open' }),
        },
      },
    )
    return response.data
  }
}

export const monitoringApiService = new MonitoringApiService()
