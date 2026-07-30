<script setup lang="ts">
import { Badge } from '@/components/ui/badge'

defineProps<{
  title: string
  count?: number
  description?: string
}>()
</script>

<template>
  <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
    <!-- Left section: Title + count -->
    <div class="flex items-center gap-3">
      <h1 class="text-2xl font-bold text-foreground">
        {{ title }}
      </h1>
      <Badge v-if="count !== undefined" variant="secondary">
        {{ count }}
      </Badge>
    </div>

    <!-- Right section: Actions slot -->
    <div v-if="$slots.actions" class="flex items-center gap-2">
      <slot name="actions" />
    </div>
  </div>

  <!-- Optional description -->
  <p v-if="description" class="text-sm text-muted-foreground mb-4">
    {{ description }}
  </p>
</template>
