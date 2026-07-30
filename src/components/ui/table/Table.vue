<script setup lang="ts">
import { type HTMLAttributes, useTemplateRef } from 'vue'
import { cn } from '@/lib/utils'

const props = defineProps<{
  class?: HTMLAttributes['class']
  ariaLabel?: string
  ariaLabelledby?: string
}>()

const tableContainerRef = useTemplateRef<HTMLDivElement>('tableContainerRef')

defineExpose({
  tableContainerRef,
})
</script>

<template>
  <div
    ref="tableContainerRef"
    data-slot="table-container"
    class="relative w-full overflow-x-auto overflow-y-visible"
  >
    <table
      data-slot="table"
      :class="cn('w-full caption-bottom text-sm min-w-lg', props.class)"
      :aria-label
      :aria-labelledby
    >
      <slot />
    </table>
  </div>
</template>
