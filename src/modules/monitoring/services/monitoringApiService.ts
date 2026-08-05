import { apiClient } from '@/shared/services/apiClient'
import type {
  MonitoredInstanceList,
  QueryPeriodComparison,
  QueryPeriodComparisonParams,
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
}

export const monitoringApiService = new MonitoringApiService()
