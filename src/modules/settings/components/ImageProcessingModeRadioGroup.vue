<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { Label } from '@/components/ui/label'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'

const { t } = useI18n()

const props = defineProps<{
  modelValue?: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()
</script>

<template>
  <RadioGroup
    class="flex flex-col gap-4"
    :model-value="props.modelValue"
    @update:model-value="value => { if (typeof value === 'string') emit('update:modelValue', value) }"
  >
    <div class="flex items-center gap-2">
      <RadioGroupItem id="high-quality" value="high_quality" />
      <div class="flex-1">
        <Label for="high-quality" class="text-sm font-medium cursor-pointer">
          {{ t('settings.preferences.imageProcessingMode.options.highQuality') }}
        </Label>
        <p class="text-xs text-muted-foreground">
          {{ t('settings.preferences.imageProcessingMode.options.highQualityDescription') }}
        </p>
      </div>
    </div>
    <div class="flex items-center gap-2">
      <RadioGroupItem id="balanced" value="balanced" />
      <div class="flex-1">
        <Label for="balanced" class="text-sm font-medium cursor-pointer">
          {{ t('settings.preferences.imageProcessingMode.options.balanced') }}
        </Label>
        <p class="text-xs text-muted-foreground">
          {{ t('settings.preferences.imageProcessingMode.options.balancedDescription') }}
        </p>
      </div>
    </div>
    <div class="flex items-center gap-2">
      <RadioGroupItem id="storage-saver" value="storage_saver" />
      <div class="flex-1">
        <Label for="storage-saver" class="text-sm font-medium cursor-pointer">
          {{ t('settings.preferences.imageProcessingMode.options.storageSaver') }}
        </Label>
        <p class="text-xs text-muted-foreground">
          {{ t('settings.preferences.imageProcessingMode.options.storageSaverDescription') }}
        </p>
      </div>
    </div>
  </RadioGroup>
</template>

