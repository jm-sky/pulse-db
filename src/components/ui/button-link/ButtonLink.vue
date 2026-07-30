<script setup lang="ts">
import { type RouteLocationRaw, RouterLink } from 'vue-router'
import { Button, type ButtonProps } from '@/components/ui/button'
import { cn } from '@/lib/utils'

interface Props extends Omit<ButtonProps, 'as'> {
  to: RouteLocationRaw
  replace?: boolean
  activeClass?: string
  exactActiveClass?: string
  custom?: boolean
  ariaCurrentValue?: 'true' | 'false' | 'page' | 'step' | 'location' | 'date' | 'time'
  class?: string
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'default',
  size: 'default',
  replace: false,
  custom: false,
  loading: false,
  disabled: false
})

// Merge RouterLink props with Button props
const linkProps = {
  to: props.to,
  replace: props.replace,
  activeClass: props.activeClass,
  exactActiveClass: props.exactActiveClass,
  custom: props.custom,
  ariaCurrentValue: props.ariaCurrentValue
}

const buttonProps: Omit<ButtonProps, 'as'> = {
  variant: props.variant,
  size: props.size,
  vibe: props.vibe,
  loading: props.loading,
  disabled: props.disabled,
  class: cn(props.class)
}
</script>

<template>
  <RouterLink v-slot="{ href, navigate }" v-bind="linkProps" custom>
    <Button
      v-bind="buttonProps"
      as="a"
      :href="href"
      @click="navigate"
    >
      <slot />
    </Button>
  </RouterLink>
</template>
