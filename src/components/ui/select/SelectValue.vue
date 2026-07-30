<script setup lang="ts">
import { SelectValue } from 'reka-ui'
import type { SelectValueProps } from 'reka-ui'

const props = defineProps<SelectValueProps>()
</script>

<template>
  <SelectValue
    data-slot="select-value"
    v-bind="props"
  >
    <template #default="{ selectedLabel, modelValue }">
      <slot :selected-label :model-value />
    </template>
  </SelectValue>
</template>
