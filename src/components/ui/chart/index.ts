import { createContext } from 'reka-ui'
import { defineAsyncComponent } from 'vue'
import type { Component, Ref } from 'vue'

export { default as ChartContainer } from './ChartContainer.vue'
export { default as ChartLegendContent } from './ChartLegendContent.vue'
export { default as ChartTooltipContent } from './ChartTooltipContent.vue'
export { componentToString } from './utils'

// Format: { THEME_NAME: CSS_SELECTOR }
export const THEMES = { light: '', dark: '.dark' } as const

export type ChartConfig = {
  [k in string]: {
    label?: string | Component
    icon?: string | Component
  } & (
    | { color?: string, theme?: never }
    | { color?: never, theme: Record<keyof typeof THEMES, string> }
  )
}

interface ChartContextProps {
  id: string
  config: Ref<ChartConfig>
}

export const [useChart, provideChartContext] = createContext<ChartContextProps>('Chart')

// Lazy load @unovis/vue components to avoid loading the entire library when not needed
// These should be imported dynamically in components that use them
export const ChartCrosshair = defineAsyncComponent(() => import('@unovis/vue').then(m => m.VisCrosshair))
export const ChartTooltip = defineAsyncComponent(() => import('@unovis/vue').then(m => m.VisTooltip))
