<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import Button from '@/components/ui/button/Button.vue'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

const open = defineModel<boolean>('open', { required: true })
const props = defineProps<{
  title: string
  description: string
  confirmLabel?: string
  loading?: boolean
}>()
const emit = defineEmits<{ confirm: [] }>()

const { t } = useI18n()
</script>

<template>
  <Dialog v-model:open="open">
    <DialogContent class="sm:max-w-md">
      <DialogHeader>
        <DialogTitle>{{ props.title }}</DialogTitle>
        <DialogDescription>{{ props.description }}</DialogDescription>
      </DialogHeader>
      <DialogFooter>
        <Button
          type="button"
          variant="outline"
          :disabled="props.loading"
          @click="open = false"
        >
          {{ t('common.cancel', 'Cancel') }}
        </Button>
        <Button
          type="button"
          variant="destructive"
          :disabled="props.loading"
          @click="emit('confirm')"
        >
          {{ props.loading ? t('common.deleting', 'Deleting…') : (props.confirmLabel ?? t('common.delete', 'Delete')) }}
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
