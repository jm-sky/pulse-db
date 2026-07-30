<script setup lang="ts">
import { type RouteLocationRaw, RouterLink } from 'vue-router'
import { cn } from '@/lib/utils'

defineProps<{
  to: RouteLocationRaw
  ariaLabel?: string
  activeClass?: string
  exactActiveClass?: string
}>()
</script>

<template>
  <RouterLink
    :to
    :aria-label="ariaLabel"
    class="relative before:absolute before:-bottom-0.5 before:rounded-md before:h-0.5 before:w-0 before:bg-primary before:transition-all before:duration-300 before:ease-in-out hover:before:w-full hover:text-primary hover:bg-transparent dark:hover:bg-transparent"
    :active-class="cn('before:w-full text-primary bg-transparent dark:bg-transparent hover:brightness-90 dark:hover:brightness-110', activeClass)"
    :exact-active-class="cn('before:w-full text-primary bg-transparent dark:bg-transparent hover:brightness-90 dark:hover:brightness-110', exactActiveClass)"
  >
    <slot />
  </RouterLink>
</template>
