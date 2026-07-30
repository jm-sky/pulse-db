<script setup lang="ts">
import { PlusIcon } from 'lucide-vue-next'
import Button from '../button/Button.vue'
import { useCommand } from '../command'

const { filterState } = useCommand()

defineProps<{
  createLabel: string
}>()

const emit = defineEmits<{
  create: [value: string]
}>()
</script>

<template>
  <Button variant="outline" size="sm" @click="emit('create', filterState.search)">
    <PlusIcon class="size-4" />
    {{ createLabel }}
  </Button>
</template>
