<script setup lang="ts">
const visible = defineModel<boolean>('visible', { required: true })

defineProps<{
  title: string
  progressText: string
  progressPercentage: number
  currentItemText: string
  current: number
  total: number
}>()
</script>

<template>
  <div
    v-if="visible"
    class="absolute inset-1 bg-background/30 backdrop-blur-xs z-50 flex flex-col items-center justify-center p-8 rounded-lg"
  >
    <div class="w-full max-w-md space-y-4">
      <div class="text-center space-y-2">
        <h3 class="text-lg font-semibold">
          {{ title }}
        </h3>
        <p class="text-sm text-muted-foreground">
          {{ currentItemText }}
        </p>
      </div>

      <!-- Progress Bar -->
      <div class="space-y-2">
        <div class="h-2 w-full overflow-hidden rounded-full bg-muted">
          <div
            class="h-full bg-primary transition-all duration-300"
            :style="{ width: `${progressPercentage}%` }"
          />
        </div>
        <div class="flex items-center justify-between text-xs text-muted-foreground">
          <span>
            {{ progressText }}: {{ current }} / {{ total }}
          </span>
          <span>{{ progressPercentage }}%</span>
        </div>
      </div>
    </div>
  </div>
</template>
