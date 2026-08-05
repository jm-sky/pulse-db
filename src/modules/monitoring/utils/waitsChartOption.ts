import type { EChartsOption } from 'echarts'
import type { WaitsTimeline } from '@/modules/monitoring/types/monitoring.type'

/** Layout constants — legend top, main grid, dataZoom slider band at bottom. */
const LEGEND_TOP = 4
const GRID_TOP = 36
const GRID_BOTTOM = 88
const SLIDER_HEIGHT = 40
const SLIDER_BOTTOM = 12

function chartCssColor(index: number): string {
  const slot = (index % 5) + 1
  return getComputedStyle(document.documentElement).getPropertyValue(`--chart-${slot}`).trim()
}

function formatBucketLabel(bucketStart: string, granularity: WaitsTimeline['granularity']): string {
  const date = new Date(bucketStart)
  if (granularity === '1h') {
    return date.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit' })
  }
  return date.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })
}

export function buildWaitsChartOption(timeline: WaitsTimeline): EChartsOption {
  const bucketStarts = [...new Set(
    timeline.series.flatMap(series => series.points.map(point => point.bucketStart)),
  )].sort()

  const xLabels = bucketStarts.map(bucket => formatBucketLabel(bucket, timeline.granularity))

  const series = timeline.series.map((waitSeries, index) => {
    const byBucket = new Map(waitSeries.points.map(point => [point.bucketStart, point.waitSeconds]))
    return {
      name: waitSeries.label,
      type: 'bar' as const,
      stack: 'waits',
      emphasis: { focus: 'series' as const },
      itemStyle: { color: chartCssColor(index) },
      data: bucketStarts.map(bucket => byBucket.get(bucket) ?? 0),
    }
  })

  return {
    animation: false,
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      valueFormatter: (value) => {
        const numeric = typeof value === 'number' ? value : Number(value)
        return `${numeric.toFixed(2)} s`
      },
    },
    legend: {
      type: 'scroll',
      top: LEGEND_TOP,
      left: 'center',
      textStyle: { color: 'var(--muted-foreground)' },
    },
    grid: {
      left: 52,
      right: 20,
      top: GRID_TOP,
      bottom: GRID_BOTTOM,
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      data: xLabels,
      axisLabel: { color: 'var(--muted-foreground)' },
      axisLine: { lineStyle: { color: 'var(--border)' } },
    },
    yAxis: {
      type: 'value',
      name: 'Wait (s)',
      nameTextStyle: { color: 'var(--muted-foreground)' },
      axisLabel: { color: 'var(--muted-foreground)' },
      splitLine: { lineStyle: { color: 'var(--border)' } },
    },
    dataZoom: [
      {
        type: 'inside',
        xAxisIndex: 0,
        filterMode: 'filter',
      },
      {
        type: 'slider',
        xAxisIndex: 0,
        height: SLIDER_HEIGHT,
        bottom: SLIDER_BOTTOM,
        borderColor: 'var(--border)',
        backgroundColor: 'color-mix(in oklch, var(--muted) 60%, transparent)',
        fillerColor: 'color-mix(in oklch, var(--chart-1) 30%, transparent)',
        handleStyle: { color: 'var(--chart-1)', borderColor: 'var(--chart-1)' },
        dataBackground: {
          lineStyle: { color: 'var(--chart-2)', opacity: 0.45 },
          areaStyle: { color: 'color-mix(in oklch, var(--chart-2) 20%, transparent)' },
        },
        selectedDataBackground: {
          lineStyle: { color: 'var(--chart-1)', opacity: 0.6 },
          areaStyle: { color: 'color-mix(in oklch, var(--chart-1) 25%, transparent)' },
        },
        textStyle: { color: 'var(--muted-foreground)' },
        brushSelect: false,
      },
    ],
    series,
  }
}

export const WAITS_CHART_LAYOUT = {
  legendTop: LEGEND_TOP,
  gridTop: GRID_TOP,
  gridBottom: GRID_BOTTOM,
  sliderHeight: SLIDER_HEIGHT,
  sliderBottom: SLIDER_BOTTOM,
} as const
