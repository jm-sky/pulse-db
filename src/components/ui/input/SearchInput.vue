<script setup lang="ts">
import { Search, XIcon } from 'lucide-vue-next'
import { Input } from '@/components/ui/input'
import { cn } from '@/lib/utils'
import Button from '../button/Button.vue'
import type { HTMLAttributes } from 'vue'

const modelValue = defineModel<string>('modelValue', { default: '' })

const props = defineProps<{
  id?: string
  name?: string
  placeholder?: string
  class?: HTMLAttributes['class']
  disabled?: boolean
}>()
</script>

<template>
  <div class="relative inline-flex flex-1 w-full">
    <Search class="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
    <Input
      :id="id ?? 'search'"
      v-model="modelValue"
      :name="name ?? 'search'"
      :placeholder
      :disabled
      :class="cn('pl-9', props.class)"
    />
    <Button
      v-if="modelValue"
      variant="ghost"
      size="sm"
      class="absolute right-3 top-1/2 size-4 -translate-y-1/2"
      @click="modelValue = ''"
    >
      <XIcon class="size-4" />
    </Button>
  </div>
</template>
