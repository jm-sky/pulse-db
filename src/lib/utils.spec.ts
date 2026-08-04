import { describe, expect, it } from 'vitest'
import { ref } from 'vue'
import { cn, valueUpdater } from './utils'

describe('utils', () => {
  describe('cn', () => {
    it('should merge class names correctly', () => {
      expect(cn('foo', 'bar')).toBe('foo bar')
    })

    it('should handle conditional classes', () => {
      expect(cn('foo', false && 'bar', 'baz')).toBe('foo baz')
      expect(cn('foo', true && 'bar', 'baz')).toBe('foo bar baz')
    })

    it('should handle arrays', () => {
      expect(cn(['foo', 'bar'])).toBe('foo bar')
      expect(cn('foo', ['bar', 'baz'])).toBe('foo bar baz')
    })

    it('should handle objects', () => {
      expect(cn({ foo: true, bar: false, baz: true })).toBe('foo baz')
    })

    it('should merge Tailwind classes correctly', () => {
      // Tailwind merge should deduplicate conflicting classes
      expect(cn('px-2 py-1', 'px-4')).toContain('px-4')
      expect(cn('px-2 py-1', 'px-4')).not.toContain('px-2')
    })

    it('should handle empty inputs', () => {
      expect(cn()).toBe('')
      expect(cn('')).toBe('')
      expect(cn(null, undefined)).toBe('')
    })

    it('should handle mixed inputs', () => {
      expect(cn('foo', ['bar'], { baz: true }, 'qux')).toBe('foo bar baz qux')
    })
  })

  describe('valueUpdater', () => {
    it('should update ref with direct value', () => {
      const refValue = ref('initial')
      valueUpdater('updated', refValue)
      expect(refValue.value).toBe('updated')
    })

    it('should update ref with function updater', () => {
      const refValue = ref(5)
      valueUpdater((prev: number) => prev + 1, refValue)
      expect(refValue.value).toBe(6)
    })

    it('should handle number values', () => {
      const refValue = ref(0)
      valueUpdater(42, refValue)
      expect(refValue.value).toBe(42)
    })

    it('should handle boolean values', () => {
      const refValue = ref(false)
      valueUpdater(true, refValue)
      expect(refValue.value).toBe(true)
    })

    it('should handle object values', () => {
      const refValue = ref({ foo: 'bar' })
      valueUpdater({ foo: 'baz', qux: 'quux' }, refValue)
      expect(refValue.value).toEqual({ foo: 'baz', qux: 'quux' })
    })

    it('should handle array values', () => {
      const refValue = ref([1, 2, 3])
      valueUpdater([4, 5, 6], refValue)
      expect(refValue.value).toEqual([4, 5, 6])
    })

    it('should handle function updater with previous value', () => {
      const refValue = ref(10)
      valueUpdater((prev: number) => prev * 2, refValue)
      expect(refValue.value).toBe(20)
    })

    it('should handle function updater with object', () => {
      const refValue = ref({ count: 1, name: 'test' })
      valueUpdater((prev: { count: number; name: string }) => ({ ...prev, count: prev.count + 1 }), refValue)
      expect(refValue.value).toEqual({ count: 2, name: 'test' })
    })
  })
})

