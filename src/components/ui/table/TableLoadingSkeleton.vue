<script setup lang="ts">
import { Loader2 } from 'lucide-vue-next'
import TableEmpty from './TableEmpty.vue'

withDefaults(defineProps<{
  colspan?: number
  message?: string
}>(), {
  colspan: 1,
  message: 'Loading...',
})
</script>

<template>
  <TableEmpty :colspan="colspan" class="flex w-[calc(100vw-2rem)] md:w-auto md:table-cell">
    <div class="w-full flex flex-col items-center justify-center py-12 text-center">
      <div class="rounded-full bg-muted p-6 mb-4">
        <Loader2 class="size-12 text-muted-foreground animate-spin" />
      </div>
      <p class="text-muted-foreground">
        {{ message }}
      </p>
      <slot />
    </div>
  </TableEmpty>
</template>
