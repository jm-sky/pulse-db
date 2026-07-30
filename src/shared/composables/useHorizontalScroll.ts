import { type ComputedRef, onMounted, onUnmounted, ref, type Ref } from 'vue'

export interface HorizontalScrollState {
  hasHorizontalScroll: Ref<boolean>
  canScrollLeft: Ref<boolean>
  canScrollRight: Ref<boolean>
  updateScrollState: () => void
}

/**
 * Composable for tracking horizontal scroll state of an element
 * Useful for showing/hiding shadows on pinned columns or other scroll-dependent UI
 *
 * @param scrollElementRef - Ref to the scrollable element (HTMLDivElement or similar)
 * @returns Reactive state and update function
 *
 * @example
 * ```vue
 * <script setup>
 * const containerRef = useTemplateRef<HTMLDivElement>('container')
 * const { hasHorizontalScroll, canScrollLeft, canScrollRight } = useHorizontalScroll(containerRef)
 * </script>
 *
 * <template>
 *   <div ref="container" class="overflow-x-auto">
 *     <div :class="{ 'shadow-lg': canScrollLeft }">...</div>
 *   </div>
 * </template>
 * ```
 */
export function useHorizontalScroll(
  scrollElementRef: Ref<HTMLElement | null | undefined> | ComputedRef<HTMLElement | null | undefined>,
): HorizontalScrollState {
  const hasHorizontalScroll = ref<boolean>(false)
  const canScrollLeft = ref<boolean>(false)
  const canScrollRight = ref<boolean>(false)

  const updateScrollState = () => {
    const el = scrollElementRef.value
    if (!el) return

    const { scrollLeft, scrollWidth, clientWidth } = el
    hasHorizontalScroll.value = scrollWidth > clientWidth + 1
    canScrollLeft.value = scrollLeft > 0
    canScrollRight.value = scrollLeft + clientWidth < scrollWidth - 1
  }

  onMounted(() => {
    updateScrollState()
    const el = scrollElementRef.value
    if (el) {
      el.addEventListener('scroll', updateScrollState, { passive: true })
    }
    window.addEventListener('resize', updateScrollState)
  })

  onUnmounted(() => {
    const el = scrollElementRef.value
    if (el) {
      el.removeEventListener('scroll', updateScrollState)
    }
    window.removeEventListener('resize', updateScrollState)
  })

  return {
    hasHorizontalScroll,
    canScrollLeft,
    canScrollRight,
    updateScrollState,
  }
}

