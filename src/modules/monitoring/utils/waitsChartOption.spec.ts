import { describe, expect, it } from 'vitest'
import { buildWaitsChartOption } from '@/modules/monitoring/utils/waitsChartOption'
import type { WaitsTimeline } from '@/modules/monitoring/types/monitoring.type'

describe('buildWaitsChartOption', () => {
  it('builds aligned stacked series for each wait class', () => {
    const timeline: WaitsTimeline = {
      instanceId: 'inst-1',
      granularity: '1m',
      start: '2026-08-05T09:00:00.000Z',
      end: '2026-08-05T10:00:00.000Z',
      series: [
        {
          waitClassId: 'cpu',
          label: 'CPU',
          points: [
            { bucketStart: '2026-08-05T09:00:00.000Z', waitSeconds: 1, sampleCount: 60 },
            { bucketStart: '2026-08-05T09:01:00.000Z', waitSeconds: 2, sampleCount: 58 },
          ],
        },
        {
          waitClassId: 'lock',
          label: 'Lock',
          points: [
            { bucketStart: '2026-08-05T09:00:00.000Z', waitSeconds: 0.5, sampleCount: 10 },
          ],
        },
      ],
    }

    const option = buildWaitsChartOption(timeline) as {
      series?: Array<{ name?: string, data?: number[] }>
      xAxis?: { data?: string[] }
    }
    expect(option.series?.length).toBe(2)
    const cpuSeries = option.series?.find(series => series.name === 'CPU')
    expect(cpuSeries?.data).toEqual([1, 2])
    const lockSeries = option.series?.find(series => series.name === 'Lock')
    expect(lockSeries?.data).toEqual([0.5, 0])
    expect(option.xAxis?.data?.length).toBe(2)
  })
})
