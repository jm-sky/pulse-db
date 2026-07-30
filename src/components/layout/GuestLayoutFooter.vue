<script setup lang="ts">
import { useAppVersion } from '@/shared/composables/useAppVersion'
import { config } from '@/shared/config/config'
import HoverLinkExternal from '../ui/hover-link/HoverLinkExternal.vue'

const currentYear = new Date().getFullYear()
const { version, buildDate } = useAppVersion()
</script>

<template>
  <footer>
    <div class="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
      <p class="text-center text-sm text-muted-foreground">
        &copy; {{ currentYear }}
        <HoverLinkExternal :href="config.contact.companyWebsite">
          {{ config.contact.companyName }}
        </HoverLinkExternal>
        <span class="mx-1">|</span>
        <HoverLinkExternal href="https://sava-group.pl">
          SAVA GROUP sp. z o.o.
        </HoverLinkExternal>
        <span class="mx-1">|</span>
        {{ config.app.name }}
        <span class="mx-1">|</span>
        <span>
          v{{ version }} – {{ buildDate }}
        </span>
      </p>
    </div>
  </footer>
</template>
