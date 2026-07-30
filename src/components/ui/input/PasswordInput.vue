<script setup lang="ts">
import { EyeIcon, EyeOffIcon } from 'lucide-vue-next'
import { useAttrs } from 'vue'
import { type HTMLAttributes, ref } from 'vue'
import { Input } from '@/components/ui/input'
import { cn } from '@/lib/utils'
import Button from '../button/Button.vue'

const props = defineProps<{
  placeholder?: string
  class?: HTMLAttributes['class']
}>()

const modelValue = defineModel<string>('modelValue', { default: '' })
const attrs = useAttrs()
const showPassword = ref(false)
</script>

<template>
  <div class="relative">
    <Input
      v-model="modelValue"
      v-bind="attrs"
      :placeholder="placeholder"
      :class="cn('pr-9', props.class)"
      :type="showPassword ? 'text' : 'password'"
    />
    <Button
      type="button"
      variant="ghost"
      size="sm"
      class="absolute right-3 top-1/2 size-4 -translate-y-1/2"
      @click="showPassword = !showPassword"
    >
      <EyeIcon v-if="showPassword" class="size-4" />
      <EyeOffIcon v-else class="size-4" />
    </Button>
  </div>
</template>
