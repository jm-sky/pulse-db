<script setup lang="ts" generic="T = unknown">
import { CheckIcon, ChevronsUpDownIcon, XIcon } from 'lucide-vue-next'
import { computed } from 'vue'
import { Button } from '@/components/ui/button'
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { cn } from '@/lib/utils'
import CreateOptionButton from './CreateOptionButton.vue'
import type { HTMLAttributes } from 'vue'

export interface ComboBoxOption<T = unknown> {
  value: string
  label: string
  data?: T
}

const props = withDefaults(defineProps<{
  options: ComboBoxOption[]
  placeholder?: string
  class?: HTMLAttributes['class']
  popoverContentClass?: HTMLAttributes['class']
  emptyMessage?: string
  searchPlaceholder?: string
  creatable?: boolean
  createLabel?: string
  clearable?: boolean
}>(), {
  creatable: false,
  createLabel: 'Add',
  clearable: false,
})

const open = defineModel<boolean>('open', { default: false })
const value = defineModel<string>('value', { default: '' })

// Get display value - show label if exists, otherwise show raw value
const displayValue = computed(() => {
  if (!value.value) return ''
  const option = props.options.find(opt => opt.value.toLowerCase() === value.value.toLowerCase())
  return option?.label ?? value.value
})

// Handle creating new value
function handleCreate(searchText: string) {
  if (searchText.trim()) {
    value.value = searchText.trim()
    open.value = false
  }
}

function onItemSelect(option: ComboBoxOption) {
  value.value = option.value
  open.value = false
}
</script>

<template>
  <Popover v-model:open="open">
    <div class="relative">
      <PopoverTrigger as-child>
        <Button
          variant="outline"
          role="combobox"
          :aria-expanded="open"
          :class="cn('w-full justify-between font-normal', props.class)"
        >
          <slot v-if="value" name="value">
            {{ displayValue ?? placeholder }}
          </slot>
          <span v-else>
            {{ displayValue ?? placeholder }}
          </span>
          <ChevronsUpDownIcon class="size-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <button
        v-if="clearable && value"
        type="button"
        class="cursor-pointer opacity-50 absolute top-1/2 right-10 -translate-y-1/2"
        @click.stop.prevent.capture="value = ''"
      >
        <XIcon class="size-4 shrink-0" />
      </button>
    </div>
    <PopoverContent :class="cn('w-[300px] p-0', popoverContentClass)">
      <Command>
        <CommandInput
          :placeholder="searchPlaceholder ?? 'Search options...'"
        />
        <CommandList>
          <CommandEmpty>
            {{ emptyMessage ?? 'No options found.' }}
            <div class="p-2">
              <CreateOptionButton v-if="creatable" :create-label="createLabel" @create="handleCreate" />
            </div>
          </CommandEmpty>
          <CommandGroup>
            <CommandItem
              v-for="option in options"
              :key="option.value"
              :value="option.value"
              @select="onItemSelect(option)"
            >
              <CheckIcon :class="cn('mr-2 size-4', value === option.value ? 'opacity-100' : 'opacity-0')" />
              <slot name="option-before" :option />
              <slot name="option-content" :option>
                {{ option.label }}
              </slot>
              <slot name="option-after" :option />
            </CommandItem>
          </CommandGroup>
        </CommandList>
      </Command>
    </PopoverContent>
  </Popover>
</template>
