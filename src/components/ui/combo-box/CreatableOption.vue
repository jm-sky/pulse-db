<script setup lang="ts">
import { PlusIcon } from 'lucide-vue-next'
import { computed } from 'vue'
import { CommandItem, useCommand } from '@/components/ui/command'
import type { ComboBoxOption } from './ComboBox.vue'

const props = defineProps<{
  options: ComboBoxOption[]
  createLabel: string
}>()

const emit = defineEmits<{
  create: [value: string]
}>()

const { filterState } = useCommand()

// Use filterState.search
const currentSearch = computed(() => filterState.search)

// Check if current search value is not in options and is not empty
const canCreate = computed(() => {
  if (!currentSearch.value.trim()) return false

  const searchLower = currentSearch.value.trim().toLowerCase()
  return !props.options.some(opt =>
    opt.value.toLowerCase() === searchLower ||
    opt.label.toLowerCase() === searchLower
  )
})

function handleSelect() {
  if (canCreate.value && currentSearch.value.trim()) {
    emit('create', currentSearch.value.trim())
  }
}
</script>

<template>
  <CommandItem
    v-if="true || canCreate"
    :value="currentSearch.trim()"
    class="text-primary"
    @select="handleSelect"
  >
    <PlusIcon class="mr-2 size-4" />
    {{ createLabel }} "{{ currentSearch.trim() }}"
  </CommandItem>
</template>

