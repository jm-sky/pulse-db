<script setup lang="ts">
import { cn } from '@/lib/utils'
import BackButton from './BackButton.vue'
import type { Component, HTMLAttributes } from 'vue'

const { icon, label, description } = defineProps<{
  icon?: Component
  label: string
  description?: string
  iconClass?: HTMLAttributes['class']
  withBackButton?: boolean
}>()

const emit = defineEmits<{
  back: []
}>()
</script>

<template>
  <div class="space-y-6">
    <!-- Above section (optional): back button + top actions -->
    <div v-if="$slots.above || withBackButton" class="flex items-center justify-between gap-3">
      <slot name="above">
        <slot name="back-button">
          <BackButton
            v-if="withBackButton"
            @click="emit('back')"
          />
        </slot>
        <slot name="top-actions" />
        <slot name="dropdown" />
      </slot>
    </div>

    <!-- Center section: title + actions -->
    <div class="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
      <!-- Left: icon, title, description -->
      <div class="flex-1 min-w-0">
        <div class="flex items-center gap-3">
          <slot name="before-icon" />
          <component
            :is="icon"
            v-if="icon"
            :class="cn('size-8 shrink-0 text-primary', iconClass)"
          />
          <h1 class="text-3xl font-bold tracking-tight">
            {{ label }}
          </h1>
        </div>
        <p v-if="description || $slots.description" class="text-muted-foreground mt-2">
          <slot name="description">
            {{ description }}
          </slot>
        </p>
      </div>

      <!-- Right: actions, dropdown -->
      <div v-if="$slots.actions || $slots.dropdown" class="flex items-center justify-end gap-2 flex-wrap">
        <slot name="actions" />
        <slot name="dropdown" />
      </div>
    </div>
  </div>
</template>
