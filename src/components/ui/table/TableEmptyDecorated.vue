<script setup lang="ts">
import { Package, Plus } from 'lucide-vue-next'
import { computed } from 'vue'
import { Button } from '@/components/ui/button'
import TableEmpty from './TableEmpty.vue'
import type { Component } from 'vue'

const props = withDefaults(defineProps<{
  colspan?: number
  icon?: Component
  title: string
  description: string
  showAction?: boolean
  actionText?: string
}>(), {
  colspan: 1,
  showAction: false,
})

const iconComponent = computed(() => props.icon ?? Package)

const emit = defineEmits<{
  action: []
}>()
</script>

<template>
  <TableEmpty :colspan="colspan" class="flex w-[calc(100vw-2rem)] md:w-auto md:table-cell">
    <div class="w-full flex flex-col items-center justify-center py-12 text-center">
      <div class="rounded-full bg-muted p-6 mb-4">
        <component :is="iconComponent" class="size-12 text-muted-foreground" />
      </div>
      <h3 class="text-lg font-semibold mb-2">
        {{ title }}
      </h3>
      <p class="text-muted-foreground max-w-md text-wrap mb-4">
        {{ description }}
      </p>
      <slot name="action">
        <Button v-if="showAction && actionText" @click="emit('action')">
          <Plus class="size-4" />
          {{ actionText }}
        </Button>
      </slot>
    </div>
  </TableEmpty>
</template>
