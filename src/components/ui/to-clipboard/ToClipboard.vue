<script setup lang="ts">
import { refAutoReset } from '@vueuse/core'
import { Check, Copy } from 'lucide-vue-next'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { toast } from 'vue-sonner'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { copyToClipboard } from '@/lib/copyToClipboard'
import { cn } from '@/lib/utils'

const props = withDefaults(defineProps<{
  value: string | null | undefined
  emptyText?: string
  maxWidthClass?: string
  class?: string
}>(), {
  emptyText: '—',
  maxWidthClass: 'max-w-xs',
})

const { t } = useI18n()
const copied = refAutoReset(false, 3000)

const hasValue = computed(() => Boolean(props.value))
const displayText = computed(() => props.value ?? props.emptyText)

async function copyValue() {
  if (!props.value) return

  const result = await copyToClipboard(props.value)

  if (result === 'copied') {
    copied.value = true
    toast.success(t('common.copyToClipboard.copied', 'Copied to clipboard'))
    return
  }

  toast.error(t('common.copyFailed', 'Failed to copy'))
}
</script>

<template>
  <Tooltip :delay-duration="150">
    <TooltipTrigger as-child>
      <button
        type="button"
        :disabled="!hasValue"
        :title="value ?? undefined"
        :class="cn(
          'inline-flex items-center gap-1 rounded-md border border-border bg-muted/40 px-2 py-0.5 text-xs leading-5',
          'hover:bg-muted transition-colors disabled:cursor-default disabled:opacity-70',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
          maxWidthClass,
          props.class,
          copied && 'opacity-60'
        )"
        @click="copyValue"
      >
        <Check v-if="copied" class="size-3 shrink-0" />
        <Copy v-else class="size-3 shrink-0" />
        <span class="truncate">
          {{ displayText }}
        </span>
      </button>
    </TooltipTrigger>
    <TooltipContent v-if="hasValue" side="top">
      {{ value }}
    </TooltipContent>
  </Tooltip>
</template>
