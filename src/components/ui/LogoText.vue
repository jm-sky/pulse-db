<script setup lang="ts">
import { cn } from '@/lib/utils'
import { config } from '@/shared/config/config'
import type { PrimitiveProps } from 'reka-ui'
import type { HTMLAttributes } from 'vue'

const props = withDefaults(defineProps<{
  as?: PrimitiveProps['as']
  class?: HTMLAttributes['class']
}>(), {
  as: 'span',
})
</script>

<template>
  <component :is="props.as" :class="cn('text-2xl font-bold text-transparent bg-clip-text bg-linear-to-r from-primary via-red-700 to-primary', props.class)">
    {{ config.app.name }}
  </component>
</template>
