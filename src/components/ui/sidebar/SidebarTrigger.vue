<script setup lang="ts">
import { PanelLeft } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { useSidebar } from './utils'
import type { HTMLAttributes } from 'vue'

const props = defineProps<{
  class?: HTMLAttributes['class']
}>()

const { toggleSidebar } = useSidebar()
const { t } = useI18n()
</script>

<template>
  <Button
    v-tooltip.bottom="t('common.toggleSidebar')"
    data-sidebar="trigger"
    data-slot="sidebar-trigger"
    variant="ghost"
    size="icon"
    :aria-label="t('common.toggleSidebar')"
    :class="cn('size-7 hover:opacity-50', props.class)"
    @click="toggleSidebar"
  >
    <PanelLeft />
    <span class="sr-only">{{ t('common.toggleSidebar') }}</span>
  </Button>
</template>
