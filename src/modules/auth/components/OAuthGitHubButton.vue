<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { Button } from '@/components/ui/button'
import GithubIcon from '@/components/ui/icons/GithubIcon.vue'
import { useOAuth } from '@/shared/composables/useOAuth'

const { t } = useI18n()
const { initiateGithubLogin, isGithubPending } = useOAuth()
</script>

<template>
  <Button
    type="button"
    variant="outline"
    size="lg"
    class="w-full"
    :disabled="isGithubPending"
    @click="initiateGithubLogin"
  >
    <GithubIcon class="size-5" />
    {{ isGithubPending ? t('auth.oauth.button.redirecting') : t('auth.oauth.button.continue_with_github') }}
  </Button>
</template>
