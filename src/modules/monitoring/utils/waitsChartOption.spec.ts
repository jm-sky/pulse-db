import { describe, expect, it } from 'vitest'
import { buildWaitsChartOption, resolveCssColorToRgb } from '@/modules/monitoring/utils/waitsChartOption'
import type { WaitsTimeline } from '@/modules/monitoring/types/monitoring.type'

describe('resolveCssColorToRgb', () => {
  it('passes through rgb and hex (zrender-safe)', () => {
    expect(resolveCssColorToRgb('rgb(1, 2, 3)')).toBe('rgb(1, 2, 3)')
    expect(resolveCssColorToRgb('#aabbcc')).toBe('#aabbcc')
  })

  it('falls back when color is empty', () => {
    expect(resolveCssColorToRgb('')).toBe('rgb(128, 128, 128)')
  })
})

describe('buildWaitsChartOption', () => {
  it('builds aligned stacked series with rgb colors and no axisPointer band', () => {
    document.documentElement.style.setProperty('--chart-1', '#9b59e6')
    document.documentElement.style.setProperty('--chart-2', '#2a9d8f')
    document.documentElement.style.setProperty('--muted-foreground', '#888888')
    document.documentElement.style.setProperty('--border', '#cccccc')

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
      series?: Array<{
        name?: string
        data?: number[]
        itemStyle?: { color?: string }
        emphasis?: { focus?: string, itemStyle?: { color?: string } }
      }>
      xAxis?: { data?: string[] }
      tooltip?: { axisPointer?: { type?: string, shadowStyle?: { color?: string } } }
    }
    expect(option.series?.length).toBe(2)
    const cpuSeries = option.series?.find(series => series.name === 'CPU')
    expect(cpuSeries?.data).toEqual([1, 2])
    expect(cpuSeries?.emphasis?.focus).toBe('none')
    expect(cpuSeries?.itemStyle?.color).toMatch(/^(#|rgb)/i)
    expect(cpuSeries?.emphasis?.itemStyle?.color).toBe(cpuSeries?.itemStyle?.color)
    const lockSeries = option.series?.find(series => series.name === 'Lock')
    expect(lockSeries?.data).toEqual([0.5, 0])
    expect(option.xAxis?.data?.length).toBe(2)
    expect(option.tooltip?.axisPointer?.type).toBe('shadow')
    expect(option.tooltip?.axisPointer?.shadowStyle?.color).toMatch(/^rgba\(/)
  })
})
