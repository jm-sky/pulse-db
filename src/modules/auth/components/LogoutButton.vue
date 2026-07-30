<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/modules/auth/composables/useAuth'

const { logout, isLoggingOut } = useAuth()
const { t } = useI18n()
</script>

<template>
  <Button variant="ghost" :loading="isLoggingOut" @click="logout">
    {{ t('auth.logout') }}
  </Button>
</template>
