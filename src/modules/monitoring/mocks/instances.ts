export type EngineKind = 'postgresql' | 'sqlserver'

export type CollectorStatus = 'ok' | 'degraded' | 'unknown'

export interface MockInstance {
  id: string
  name: string
  engine: EngineKind
  host: string
  collectorStatus: CollectorStatus
  lastSampleAt: string
}

/** Mock estate for shell development — replace with API when REST exists. */
export const MOCK_INSTANCES: MockInstance[] = [
  {
    id: 'inst-pg-prod',
    name: 'pg-prod',
    engine: 'postgresql',
    host: 'db-prod.internal:5432',
    collectorStatus: 'ok',
    lastSampleAt: '2026-08-04T12:02:11Z',
  },
  {
    id: 'inst-sql-01',
    name: 'sql-01',
    engine: 'sqlserver',
    host: 'sql01.internal:1433',
    collectorStatus: 'ok',
    lastSampleAt: '2026-08-04T12:01:58Z',
  },
  {
    id: 'inst-pg-dev',
    name: 'pg-dev',
    engine: 'postgresql',
    host: 'localhost:5432',
    collectorStatus: 'degraded',
    lastSampleAt: '2026-08-04T11:48:03Z',
  },
]

export const MOCK_WAIT_SERIES = [
  { key: 'CPU', color: 'bg-chart-1', values: [12, 18, 22, 15, 28, 35, 30, 24, 20, 16, 14, 19] },
  { key: 'IO', color: 'bg-chart-2', values: [8, 10, 14, 20, 18, 12, 9, 11, 16, 22, 19, 13] },
  { key: 'Lock', color: 'bg-chart-3', values: [2, 4, 6, 18, 25, 14, 8, 5, 3, 7, 10, 6] },
  { key: 'Network', color: 'bg-chart-4', values: [1, 1, 2, 2, 3, 2, 1, 1, 2, 2, 1, 1] },
  { key: 'Other', color: 'bg-chart-5', values: [3, 2, 4, 3, 5, 4, 3, 2, 3, 4, 3, 2] },
] as const
