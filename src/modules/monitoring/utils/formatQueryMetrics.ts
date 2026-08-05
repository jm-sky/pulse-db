/** Compact number formatting for Queries table cells. */

export function formatCalls(value: number | null | undefined): string {
  if (value == null) return '—'
  return new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 }).format(value)
}

export function formatMs(value: number | null | undefined): string {
  if (value == null) return '—'
  if (Math.abs(value) >= 1000) {
    return `${new Intl.NumberFormat(undefined, { maximumFractionDigits: 1 }).format(value / 1000)} s`
  }
  return `${new Intl.NumberFormat(undefined, { maximumFractionDigits: 1 }).format(value)} ms`
}

export function formatDeltaPct(value: number | null | undefined): string {
  if (value == null) return '—'
  const sign = value > 0 ? '+' : ''
  return `${sign}${new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 }).format(value)}%`
}

export function truncateSql(text: string | null | undefined, max = 96): string {
  if (!text) return '—'
  const normalized = text.replace(/\s+/g, ' ').trim()
  if (normalized.length <= max) return normalized
  return `${normalized.slice(0, max - 1)}…`
}
