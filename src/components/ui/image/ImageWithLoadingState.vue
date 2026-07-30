<script setup lang="ts">
import { LoaderCircle } from 'lucide-vue-next'
import { computed, onMounted, ref, watch } from 'vue'
import type { HTMLAttributes } from 'vue'

const props = defineProps<{
  src: string
  alt?: string
  /**
   * Tailwind classes applied to the outer container.
   * Should typically include fixed sizing (e.g. size-12).
   */
  class?: HTMLAttributes['class']
  /**
   * Tailwind classes applied directly to the <img> element.
   * Defaults to 'object-cover size-full'.
   */
  imageClass?: HTMLAttributes['class']
}>()

const isLoaded = ref(false)
const hasError = ref(false)

const showSpinner = computed(() => !isLoaded.value && !hasError.value)

function resetState() {
  isLoaded.value = false
  hasError.value = false
}

function handleLoad() {
  isLoaded.value = true
}

function handleError() {
  hasError.value = true
  isLoaded.value = true
}

watch(
  () => props.src,
  () => {
    resetState()
  }
)

onMounted(() => {
  if (!props.src) {
    hasError.value = true
    isLoaded.value = true
  }
})
</script>

<template>
  <div
    :class="[
      'relative overflow-hidden rounded-md border border-border',
      props.class
    ]"
  >
    <img
      :src="props.src"
      :alt="props.alt"
      loading="lazy"
      :class="[
        'transition-opacity duration-200',
        showSpinner ? 'opacity-0' : 'opacity-100',
        props.imageClass || 'size-full object-cover'
      ]"
      @load="handleLoad"
      @error="handleError"
    />

    <div
      v-if="showSpinner"
      class="absolute inset-0 flex items-center justify-center bg-muted/40"
    >
      <LoaderCircle class="size-4 animate-spin text-muted-foreground" />
    </div>
  </div>
</template>


