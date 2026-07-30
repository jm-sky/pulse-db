<script setup lang="ts">
import { Mail } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import AuthenticatedLayout from '@/layouts/AuthenticatedLayout.vue'
import { config } from '@/shared/config/config'

const { t } = useI18n()
</script>

<template>
  <AuthenticatedLayout>
    <div class="space-y-6">
      <div class="space-y-2">
        <h1 class="text-3xl font-bold tracking-tight">
          {{ t('contact.title', 'Kontakt') }}
        </h1>
        <p class="text-muted-foreground">
          {{ t('contact.subtitle', 'Skontaktuj się z nami') }}
        </p>
      </div>

      <div class="space-y-6">
        <section class="space-y-3">
          <h2 class="text-2xl font-semibold">
            {{ t('contact.info.title', 'Informacje kontaktowe') }}
          </h2>
          <p class="text-muted-foreground">
            {{ t('contact.info.description', 'Jeśli masz pytania, sugestie lub chcesz zgłosić problem, skontaktuj się z nami:') }}
          </p>
        </section>

        <section class="space-y-3">
          <div class="flex items-center gap-4">
            <Mail class="size-5 text-muted-foreground" />
            <div>
              <p class="font-medium">
                {{ t('contact.email.label', 'Email') }}
              </p>
              <a :href="`mailto:${config.contact.email}`" class="text-primary hover:underline">
                {{ config.contact.email }}
              </a>
            </div>
          </div>
        </section>

        <section class="space-y-3">
          <h2 class="text-2xl font-semibold">
            {{ t('contact.support.title', 'Wsparcie') }}
          </h2>
          <p class="text-muted-foreground">
            {{ t('contact.support.description', 'Staramy się odpowiadać na wszystkie wiadomości w ciągu 24-48 godzin. Jeśli zgłaszasz problem techniczny, prosimy o dołączenie szczegółowych informacji o problemie.') }}
          </p>
        </section>
      </div>
    </div>
  </AuthenticatedLayout>
</template>

