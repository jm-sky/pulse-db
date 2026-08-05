export type EngineKind = 'postgresql' | 'sqlserver'

export type CollectorStatus = 'ok' | 'degraded' | 'unknown'

export interface MonitoredInstance {
  id: string
  name: string
  engine: EngineKind
  host: string
  port: number
  isActive: boolean
  collectorStatus: CollectorStatus
  lastSampleAt: string | null
}

export interface MonitoredInstanceList {
  instances: MonitoredInstance[]
}

export interface WaitsTimelinePoint {
  bucketStart: string
  waitSeconds: number
  sampleCount: number
}

export interface WaitsTimelineSeries {
  waitClassId: string | null
  label: string
  points: WaitsTimelinePoint[]
}

export interface WaitsTimeline {
  instanceId: string
  granularity: '1m' | '1h'
  start: string
  end: string
  series: WaitsTimelineSeries[]
}

export interface WaitsTimelineParams {
  start: string
  end: string
  granularity?: '1m' | '1h'
}
