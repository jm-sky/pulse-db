<script setup lang="ts">
import { useDropZone } from '@vueuse/core'
import { Upload } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { cn } from '@/lib/utils'
import { usePermissions } from '@/shared/composables/usePermissions'
import { config } from '@/shared/config/config'


interface FileDropZoneProps {
  accept?: string
  maxSize?: number // in bytes (if not provided, uses config based on user permissions)
  maxFiles?: number
  disabled?: boolean
  class?: string
}

const props = withDefaults(defineProps<FileDropZoneProps>(), {
  accept: 'image/*',
  maxSize: undefined, // Will be computed from config based on user permissions
  maxFiles: 1,
  disabled: false,
})

const { isAdmin } = usePermissions()

// Compute maxSize from config if not provided as prop
const effectiveMaxSize = computed(() => {
  if (props.maxSize !== undefined) {
    return props.maxSize
  }
  // Use config values based on user permissions
  return isAdmin.value ? config.storage.maxFileSizeAdmin : config.storage.maxFileSize
})

const emit = defineEmits<{
  filesSelected: [files: File[]]
  error: [message: string]
}>()

const { t } = useI18n()
const dropZoneRef = ref<HTMLDivElement>()
const fileInput = ref<HTMLInputElement>()

function onDrop(files: File[] | null) {
  if (!files || files.length === 0) {
    return
  }

  validateAndEmitFiles(files)
}

const { isOverDropZone } = useDropZone(dropZoneRef, {
  onDrop,
  dataTypes: props.accept.split(',').map(type => type.trim()),
})

function handleClick() {
  if (props.disabled) {
    return
  }
  fileInput.value?.click()
}

function handleFileSelect(event: Event) {
  const target = event.target as HTMLInputElement
  const files = target.files

  if (!files || files.length === 0) {
    return
  }

  validateAndEmitFiles(Array.from(files))

  // Reset input
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

function validateAndEmitFiles(files: File[]) {
  // Check number of files
  if (files.length > props.maxFiles) {
    emit('error', t('fileUpload.errors.tooManyFiles', { max: props.maxFiles }))
    return
  }

  // Validate each file
  const errors: string[] = []
  const validFiles: File[] = []

  for (const file of files) {
    // Check file size
    if (file.size > effectiveMaxSize.value) {
      errors.push(t('fileUpload.errors.fileTooLarge', {
        name: file.name,
        size: (effectiveMaxSize.value / 1024 / 1024).toFixed(1),
      }))
      continue
    }

    // Check file type
    const acceptTypes = props.accept.split(',').map(type => type.trim())
    const isValidType = acceptTypes.some((type) => {
      if (type === '*') {
        return true
      }
      if (type.endsWith('/*')) {
        const category = type.split('/')[0]
        return file.type.startsWith(`${category}/`)
      }
      return file.type === type
    })

    if (!isValidType) {
      errors.push(t('fileUpload.errors.invalidType', { name: file.name }))
      continue
    }

    validFiles.push(file)
  }

  // Emit errors if any
  if (errors.length > 0) {
    emit('error', errors.join(', '))
  }

  // Emit valid files
  if (validFiles.length > 0) {
    emit('filesSelected', validFiles)
  }
}

const dropZoneClasses = computed(() =>
  cn(
    'relative flex flex-col items-center justify-center rounded-lg border-2 border-dashed transition-colors',
    'cursor-pointer p-6 sm:p-8',
    isOverDropZone.value
      ? 'border-primary bg-primary/5'
      : 'border-muted-foreground/25 hover:border-muted-foreground/50 hover:bg-accent/50',
    props.disabled && 'cursor-not-allowed opacity-50',
    props.class,
  ),
)

const formattedAcceptTypes = computed(() => {
  if (props.accept === '*' || props.accept === '*/*') {
    return t('fileUpload.formats.any')
  }
  if (props.accept === 'image/*') {
    return t('fileUpload.formats.image')
  }
  // Fallback: format the accept string
  return props.accept.replace(/image\//g, '').toUpperCase().replace(/,/g, ', ')
})

const formattedMaxSize = computed(() => {
  return t('fileUpload.limits.maxSize', { size: (effectiveMaxSize.value / 1024 / 1024).toFixed(0) })
})

const formattedMaxFiles = computed(() => {
  if (props.maxFiles === 1) {
    return t('fileUpload.limits.maxFile', { count: props.maxFiles })
  }
  return t('fileUpload.limits.maxFiles', { count: props.maxFiles })
})

const dropZoneText = computed(() => {
  if (props.disabled) {
    return t('fileUpload.dropZone.disabled')
  }
  if (isOverDropZone.value) {
    return t('fileUpload.dropZone.dragging')
  }
  return t('fileUpload.dropZone.idle')
})
</script>

<template>
  <div
    ref="dropZoneRef"
    :class="dropZoneClasses"
    @click="handleClick"
  >
    <input
      ref="fileInput"
      :accept="accept"
      :disabled="disabled"
      :multiple="maxFiles > 1"
      class="hidden"
      type="file"
      @change="handleFileSelect"
    />

    <slot>
      <div class="flex flex-col items-center gap-2 text-center">
        <div
          :class="[
            'flex size-12 items-center justify-center rounded-full transition-colors',
            isOverDropZone ? 'bg-primary/10' : 'bg-muted',
          ]"
        >
          <Upload
            :class="[
              'size-6 transition-colors',
              isOverDropZone ? 'text-primary' : 'text-muted-foreground',
            ]"
          />
        </div>

        <div class="space-y-1">
          <p class="text-sm font-medium">
            {{ dropZoneText }}
          </p>
          <p class="text-xs text-muted-foreground">
            {{ formattedAcceptTypes }}
            ({{ formattedMaxSize }}{{ maxFiles > 1 ? `, ${formattedMaxFiles}` : '' }})
          </p>
        </div>
      </div>
    </slot>
  </div>
</template>
