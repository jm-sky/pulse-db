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

export interface PeriodWindow {
  start: string
  end: string
}

export interface PeriodMetrics {
  calls: number
  totalTimeMs: number
  rowsReturned: number
  avgTimeMs: number | null
}

export interface QueryPeriodComparisonItem {
  queryId: string
  queryText: string | null
  baseline: PeriodMetrics | null
  current: PeriodMetrics | null
  avgTimeMsDelta: number | null
  avgTimeMsDeltaPct: number | null
  callsDelta: number | null
  totalTimeMsDelta: number | null
  isRegression: boolean
}

export interface QueryPeriodComparison {
  instanceId: string
  baseline: PeriodWindow
  current: PeriodWindow
  queries: QueryPeriodComparisonItem[]
}

export interface QueryPeriodComparisonParams {
  baselineStart: string
  baselineEnd: string
  currentStart: string
  currentEnd: string
  regressionsOnly?: boolean
  limit?: number
}

export type WorkspaceTab = 'waits' | 'queries' | 'indexes' | 'instance'

export interface QueryPlanItem {
  planHash: string
  planFormat: string
  firstSeen: string
  lastSeen: string
}

export interface QueryPlansList {
  instanceId: string
  queryId: string
  isPlanChange: boolean
  plans: QueryPlanItem[]
}

export interface QueryPlanDetail {
  instanceId: string
  queryId: string
  planHash: string
  planFormat: string
  planBody: string
  firstSeen: string
  lastSeen: string
}

export interface PlanChangeItem {
  queryId: string
  planHash: string
  planFormat: string
  firstSeen: string
  queryText: string | null
  planCount: number
  isPlanChange: boolean
}

export interface PlanChanges {
  instanceId: string
  since: string
  changes: PlanChangeItem[]
}

export interface BlockingEvent {
  id: string
  detectedAt: string
  blockingQueryId: string | null
  blockedQueryId: string | null
  blockedDurationMs: number | null
  details: Record<string, unknown>
}

export interface BlockingEvents {
  instanceId: string
  since: string
  events: BlockingEvent[]
}

export interface DeadlockEventSummary {
  id: string
  detectedAt: string
  victimQueryId: string | null
  victimProcessId: string | null
  hasXml: boolean
}

export interface DeadlockEvents {
  instanceId: string
  since: string
  events: DeadlockEventSummary[]
}

export interface DeadlockEventDetail {
  id: string
  instanceId: string
  detectedAt: string
  victimQueryId: string | null
  details: Record<string, unknown>
}

export interface IndexSnapshotItem {
  id: string
  databaseName: string
  schemaName: string
  tableName: string
  indexName: string
  snapshotAt: string
  sizeBytes: number | null
  scans: number | null
  isUnused: boolean
  bloatRatio: number | null
}

export interface IndexesResponse {
  instanceId: string
  snapshotAt: string | null
  indexes: IndexSnapshotItem[]
}

export interface RecommendationItem {
  id: string
  createdAt: string
  category: string
  queryId: string | null
  evidence: Record<string, unknown>
  ddlSuggestion: string | null
  status: string
}

export interface RecommendationsResponse {
  instanceId: string
  recommendations: RecommendationItem[]
}

export interface RecommendationsParams {
  category?: string
  status?: string | null
}
