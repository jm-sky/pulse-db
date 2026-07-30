<script setup lang="ts">
import { cn } from '@/lib/utils'
import type { HTMLAttributes } from 'vue'

const props = defineProps<{
  class?: HTMLAttributes['class']
  as?: string
}>()
</script>

<template>
  <component
    :is="as ?? 'div'"
    data-slot="card"
    :class="
      cn(
        'bg-card text-card-foreground flex flex-col gap-6 rounded-xl border border-border py-6 shadow-sm',
        props.class,
      )
    "
  >
    <slot />
  </component>
</template>
