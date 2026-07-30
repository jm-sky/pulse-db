<script setup lang="ts">
import { CheckIcon, XIcon } from 'lucide-vue-next'
import Button from './Button.vue'

const on = defineModel<boolean>('on', { required: true })

defineProps<{
  label?: string
}>()
</script>

<template>
  <Button
    :variant="on ? 'outline-primary' : 'outline'"
    size="sm"
    class="group rounded-full"
    @click="on = !on"
  >
    <XIcon v-if="!on" class="size-4 group-hover:hidden" />
    <CheckIcon v-else class="size-4 group-hover:hidden" />
    <XIcon v-if="on" class="size-4 hidden group-hover:block" />
    <CheckIcon v-else class="size-4 hidden group-hover:block" />
    <slot>
      {{ label }}
    </slot>
    <slot name="after" />
  </Button>
</template>
