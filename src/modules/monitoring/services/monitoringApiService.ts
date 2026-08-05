import { apiClient } from '@/shared/services/apiClient'
import type {
  MonitoredInstanceList,
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
}

export const monitoringApiService = new MonitoringApiService()
