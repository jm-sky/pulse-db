<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import HoverLink from '@/components/ui/hover-link/HoverLink.vue'
import { PublicRouteNames } from '@/router/publicRoutes'
import { useAppVersion } from '@/shared/composables/useAppVersion'
import { config } from '@/shared/config/config'
import HoverLinkExternal from '../ui/hover-link/HoverLinkExternal.vue'
import GithubIcon from '../ui/icons/GithubIcon.vue'
import RecaptchaNotice from './RecaptchaNotice.vue'

const { t } = useI18n()

const currentYear = new Date().getFullYear()
const { version, buildDate } = useAppVersion()
</script>

<template>
  <footer class="border-t bg-background/95 backdrop-blur supports-backdrop-filter:bg-background/60 mt-auto">
    <div class="mx-auto max-w-screen-2xl px-4 py-6 text-muted-foreground">
      <div class="flex flex-col items-center justify-between gap-4 md:flex-row">
        <div class="text-sm">
          &copy; {{ currentYear }}
          <HoverLinkExternal :href="config.contact.companyWebsite">
            {{ config.contact.companyName }}
          </HoverLinkExternal>
          <span class="mx-1">|</span>
          <HoverLinkExternal :href="config.contact.officialCompanyWebsite">
            {{ config.contact.officialCompanyName }}
          </HoverLinkExternal>
        </div>
        <div class="text-sm">
          <HoverLink :to="{ name: PublicRouteNames.landing }">
            {{ config.app.name }}
          </HoverLink>
          <span v-tooltip="buildDate" class="ml-2 text-xs opacity-70">
            v{{ version }}
          </span>
        </div>

        <nav class="flex flex-col sm:flex-row flex-wrap items-center justify-center gap-3 sm:gap-6 text-sm">
          <HoverLink :to="{ name: PublicRouteNames.about }">
            {{ t('common.pages.about', 'About') }}
          </HoverLink>
          <HoverLink :to="{ name: PublicRouteNames.cookies }">
            {{ t('footer.cookies', 'Informacja o ciasteczkach') }}
          </HoverLink>
          <HoverLink :to="{ name: PublicRouteNames.privacy }">
            {{ t('footer.privacy', 'Polityka prywatności') }}
          </HoverLink>
          <HoverLink :to="{ name: PublicRouteNames.terms }">
            {{ t('footer.terms', 'Regulamin') }}
          </HoverLink>
          <HoverLink :to="{ name: PublicRouteNames.contact }">
            {{ t('footer.contact', 'Kontakt') }}
          </HoverLink>
          <HoverLinkExternal
            v-if="config.app.githubUrl"
            :title="t('footer.github', 'GitHub')"
            :href="config.app.githubUrl"
            class="inline-flex items-center gap-1"
          >
            <GithubIcon class="size-4" />
          </HoverLinkExternal>
        </nav>
      </div>

      <RecaptchaNotice />
    </div>
  </footer>
</template>

