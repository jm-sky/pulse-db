import type { EChartsOption } from 'echarts'
import type { WaitsTimeline } from '@/modules/monitoring/types/monitoring.type'

/** Layout constants — legend top, main grid, dataZoom slider band at bottom. */
const LEGEND_TOP = 4
const GRID_TOP = 36
const GRID_BOTTOM = 88
const SLIDER_HEIGHT = 40
const SLIDER_BOTTOM = 12

/** Fallback when CSS vars aren't available (tests / SSR). Matches --chart-1..5 hue order. */
const FALLBACK_CHART_RGB = [
  'rgb(155, 89, 230)',
  'rgb(42, 157, 143)',
  'rgb(61, 90, 128)',
  'rgb(233, 196, 106)',
  'rgb(244, 162, 97)',
] as const

/**
 * ECharts/zrender color parser does not understand `oklch()` / `var()` /
 * `color-mix()`. Initial canvas fill may still work (browser fillStyle), but
 * hover emphasis re-parses the color → undefined → bars vanish. Always pass
 * `rgb()` / `rgba()` / hex.
 */
export function resolveCssColorToRgb(cssColor: string, fallback = 'rgb(128, 128, 128)'): string {
  const trimmed = cssColor.trim()
  if (!trimmed) return fallback
  if (/^#([0-9a-f]{3}|[0-9a-f]{6}|[0-9a-f]{8})$/i.test(trimmed)) return trimmed
  if (/^rgba?\(/i.test(trimmed)) return trimmed
  if (typeof document === 'undefined') return fallback

  const probe = document.createElement('div')
  probe.style.color = trimmed
  document.body.appendChild(probe)
  const resolved = getComputedStyle(probe).color
  document.body.removeChild(probe)
  if (!resolved || resolved === 'rgba(0, 0, 0, 0)') return fallback
  return resolved
}

function chartCssColor(index: number): string {
  const slot = (index % 5) + 1
  const fallback = FALLBACK_CHART_RGB[(slot - 1) % FALLBACK_CHART_RGB.length]
  if (typeof document === 'undefined') return fallback
  const raw = getComputedStyle(document.documentElement).getPropertyValue(`--chart-${slot}`).trim()
  return resolveCssColorToRgb(raw, fallback)
}

function themeMutedRgb(): string {
  if (typeof document === 'undefined') return 'rgb(128, 128, 128)'
  const raw = getComputedStyle(document.documentElement).getPropertyValue('--muted-foreground').trim()
  return resolveCssColorToRgb(raw, 'rgb(128, 128, 128)')
}

function themeBorderRgb(): string {
  if (typeof document === 'undefined') return 'rgb(200, 200, 200)'
  const raw = getComputedStyle(document.documentElement).getPropertyValue('--border').trim()
  return resolveCssColorToRgb(raw, 'rgb(200, 200, 200)')
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
  const muted = themeMutedRgb()
  const border = themeBorderRgb()

  const series = timeline.series.map((waitSeries, index) => {
    const byBucket = new Map(waitSeries.points.map(point => [point.bucketStart, point.waitSeconds]))
    const color = chartCssColor(index)
    return {
      name: waitSeries.label,
      type: 'bar' as const,
      stack: 'waits',
      // Keep explicit rgb on emphasis/blur — never let ECharts re-derive from oklch.
      emphasis: {
        focus: 'none' as const,
        itemStyle: {
          color,
          opacity: 1,
          shadowBlur: 6,
          shadowColor: 'rgba(0, 0, 0, 0.28)',
        },
      },
      blur: { itemStyle: { color, opacity: 1 } },
      itemStyle: { color },
      data: bucketStarts.map(bucket => byBucket.get(bucket) ?? 0),
    }
  })

  return {
    animation: false,
    tooltip: {
      trigger: 'axis',
      // Soft category highlight — must be rgba/hex (zrender); not oklch/var/color-mix.
      axisPointer: {
        type: 'shadow',
        shadowStyle: {
          color: 'rgba(100, 110, 140, 0.14)',
        },
      },
      valueFormatter: (value) => {
        const numeric = typeof value === 'number' ? value : Number(value)
        return `${numeric.toFixed(2)} s`
      },
    },
    legend: {
      type: 'scroll',
      top: LEGEND_TOP,
      left: 'center',
      textStyle: { color: muted },
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
      axisLabel: { color: muted },
      axisLine: { lineStyle: { color: border } },
    },
    yAxis: {
      type: 'value',
      name: 'Wait (s)',
      nameTextStyle: { color: muted },
      axisLabel: { color: muted },
      splitLine: { lineStyle: { color: border } },
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
        borderColor: border,
        backgroundColor: 'rgba(128, 128, 128, 0.12)',
        fillerColor: 'rgba(100, 120, 200, 0.25)',
        handleStyle: { color: chartCssColor(0), borderColor: chartCssColor(0) },
        dataBackground: {
          lineStyle: { color: chartCssColor(1), opacity: 0.45 },
          areaStyle: { color: 'rgba(42, 157, 143, 0.15)' },
        },
        selectedDataBackground: {
          lineStyle: { color: chartCssColor(0), opacity: 0.6 },
          areaStyle: { color: 'rgba(100, 120, 200, 0.2)' },
        },
        textStyle: { color: muted },
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
