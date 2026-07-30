<script setup lang="ts" generic="TData, TValue">
import { FileText } from 'lucide-vue-next'
import TableEmptyDecorated from '@/components/ui/table/TableEmptyDecorated.vue'
import type { Table } from '@tanstack/vue-table'

interface Props {
  table: Table<TData>
  columns: unknown[]
  title?: string
  description?: string
  actionText?: string
  showAction?: boolean
}

withDefaults(defineProps<Props>(), {
  title: 'No results found',
  description: 'There are no records to display.',
  actionText: 'Add New Record',
  showAction: false,
})

const emit = defineEmits<{
  action: []
}>()
</script>

<template>
  <TableEmptyDecorated
    :colspan="columns.length"
    :icon="FileText"
    :title="title"
    :description="description"
    :show-action="showAction"
    :action-text="actionText"
    @action="emit('action')"
  />
</template>
