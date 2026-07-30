<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { config } from '@/shared/config/config'
import HoverLinkExternal from '../ui/hover-link/HoverLinkExternal.vue'

const { t } = useI18n()
</script>

<template>
  <div
    v-if="config.recaptcha.enabled"
    class="mt-4 text-center text-xs text-muted-foreground"
  >
    {{ t('footer.recaptcha.notice', 'This site is protected by reCAPTCHA. The Google') }}
    <HoverLinkExternal href="https://policies.google.com/privacy" class="underline">
      {{ t('footer.recaptcha.privacy', 'Privacy Policy') }}
    </HoverLinkExternal>
    <span>{{ t('footer.recaptcha.and', ' and ') }}</span>
    <HoverLinkExternal href="https://policies.google.com/terms" class="underline">
      {{ t('footer.recaptcha.terms', 'Terms of Service') }}
    </HoverLinkExternal>
    <span>{{ t('footer.recaptcha.google', ' apply.') }}</span>
  </div>
</template>

