import { describe, expect, it } from 'vitest'
import {
  formatCalls,
  formatDeltaPct,
  formatMs,
  truncateSql,
} from '@/modules/monitoring/utils/formatQueryMetrics'

describe('formatQueryMetrics', () => {
  it('formats calls and empty values', () => {
    expect(formatCalls(null)).toBe('—')
    expect(formatCalls(1200)).toMatch(/1/)
  })

  it('formats milliseconds and seconds', () => {
    expect(formatMs(null)).toBe('—')
    expect(formatMs(12.4)).toContain('ms')
    expect(formatMs(2500)).toContain('s')
  })

  it('formats delta percent with sign', () => {
    expect(formatDeltaPct(null)).toBe('—')
    expect(formatDeltaPct(50)).toBe('+50%')
    expect(formatDeltaPct(-12.4)).toBe('-12%')
  })

  it('truncates SQL', () => {
    expect(truncateSql(null)).toBe('—')
    expect(truncateSql('SELECT  1')).toBe('SELECT 1')
    expect(truncateSql('x'.repeat(120), 20).endsWith('…')).toBe(true)
  })
})
