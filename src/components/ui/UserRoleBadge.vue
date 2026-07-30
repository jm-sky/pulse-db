<script setup lang="ts">
import { Crown, Gem, Shield } from 'lucide-vue-next'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import Badge from '@/components/ui/badge/Badge.vue'

interface Props {
  isAdmin?: boolean
  isOwner?: boolean
  isPremium?: boolean
  showIcon?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  isAdmin: false,
  isOwner: false,
  isPremium: false,
  showIcon: true,
})

const { t } = useI18n()

const roleInfo = computed(() => {
  if (props.isOwner) {
    return {
      label: t('user.roles.owner', 'Owner'),
      icon: Crown,
      class: 'bg-purple-600 hover:bg-purple-700',
    }
  }
  if (props.isPremium) {
    return {
      label: t('user.roles.premium', 'Premium'),
      icon: Gem,
      class: 'bg-yellow-600 hover:bg-yellow-700',
    }
  }
  if (props.isAdmin) {
    return {
      label: t('user.roles.admin', 'Admin'),
      icon: Shield,
      class: '',
    }
  }
  return null
})
</script>

<template>
  <Badge v-if="roleInfo" variant="default" :class="[roleInfo.class, 'gap-1']">
    <component :is="roleInfo.icon" v-if="showIcon" class="size-3" />
    {{ roleInfo.label }}
  </Badge>
</template>
