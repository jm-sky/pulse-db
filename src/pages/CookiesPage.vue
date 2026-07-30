<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import AuthenticatedLayout from '@/layouts/AuthenticatedLayout.vue'

const { t } = useI18n()
</script>

<template>
  <AuthenticatedLayout>
    <div class="space-y-6">
      <div class="space-y-2">
        <h1 class="text-3xl font-bold tracking-tight">
          {{ t('cookies.title', 'Informacja o ciasteczkach') }}
        </h1>
        <p class="text-muted-foreground">
          {{ t('cookies.subtitle', 'Informacje o wykorzystaniu danych w aplikacji') }}
        </p>
      </div>

      <div class="space-y-6">
        <section class="space-y-3">
          <h2 class="text-2xl font-semibold">
            {{ t('cookies.whatAre.title', 'Czym są pliki cookie') }}
          </h2>
          <p class="text-muted-foreground">
            {{ t('cookies.whatAre.description', 'Pliki cookie to małe pliki tekstowe, które są przechowywane na Twoim urządzeniu podczas przeglądania strony internetowej. Pomagają one aplikacji zapamiętać Twoje preferencje i zapewniają podstawowe funkcje.') }}
          </p>
        </section>

        <section class="space-y-3">
          <h2 class="text-2xl font-semibold">
            {{ t('cookies.types.title', 'Rodzaje plików cookie używanych przez nas') }}
          </h2>
          <div class="space-y-4">
            <div class="space-y-2">
              <h3 class="text-xl font-semibold">
                {{ t('cookies.types.essential.title', 'Niezbędne pliki cookie') }}
              </h3>
              <p class="text-muted-foreground">
                {{ t('cookies.types.essential.description', 'Te pliki cookie są niezbędne do działania aplikacji i nie można ich wyłączyć. Używamy ich do:') }}
              </p>
              <ul class="list-disc list-inside space-y-1 text-muted-foreground">
                <li>{{ t('cookies.types.essential.items.session', 'Utrzymania sesji użytkownika po zalogowaniu (token JWT)') }}</li>
                <li>{{ t('cookies.types.essential.items.security', 'Zapewnienia bezpieczeństwa (ochrona przed atakami CSRF)') }}</li>
                <li>{{ t('cookies.types.essential.items.preferences', 'Zapamiętania podstawowych preferencji (język, tryb ciemny)') }}</li>
              </ul>
            </div>

            <div class="space-y-2">
              <h3 class="text-xl font-semibold">
                {{ t('cookies.types.functional.title', 'Funkcjonalne pliki cookie') }}
              </h3>
              <p class="text-muted-foreground">
                {{ t('cookies.types.functional.description', 'Te pliki cookie pomagają aplikacji lepiej funkcjonować i zapamiętywać Twoje wybory:') }}
              </p>
              <ul class="list-disc list-inside space-y-1 text-muted-foreground">
                <li>{{ t('cookies.types.functional.items.settings', 'Ustawienia aplikacji przechowywane lokalnie (localStorage)') }}</li>
                <li>{{ t('cookies.types.functional.items.preferences', 'Preferencje wyświetlania i układu interfejsu') }}</li>
              </ul>
            </div>
          </div>
        </section>

        <section class="space-y-3">
          <h2 class="text-2xl font-semibold">
            {{ t('cookies.localStorage.title', 'LocalStorage') }}
          </h2>
          <p class="text-muted-foreground">
            {{ t('cookies.localStorage.description', 'Oprócz plików cookie, aplikacja wykorzystuje również localStorage przeglądarki do przechowywania niektórych danych lokalnie na Twoim urządzeniu, takich jak:') }}
          </p>
          <ul class="list-disc list-inside space-y-1 text-muted-foreground">
            <li>{{ t('cookies.localStorage.items.settings', 'Ustawienia aplikacji (preferencje językowe, jednostki wagowe)') }}</li>
            <li>{{ t('cookies.localStorage.items.cache', 'Tymczasowe dane cache do poprawy wydajności') }}</li>
            <li>{{ t('cookies.localStorage.items.offline', 'Dane offline do pracy bez połączenia z internetem') }}</li>
          </ul>
        </section>

        <section class="space-y-3">
          <h2 class="text-2xl font-semibold">
            {{ t('cookies.management.title', 'Zarządzanie plikami cookie') }}
          </h2>
          <div class="space-y-2 text-muted-foreground">
            <p>
              {{ t('cookies.management.description', 'Możesz zarządzać plikami cookie na kilka sposobów:') }}
            </p>
            <ul class="list-disc list-inside space-y-1">
              <li>{{ t('cookies.management.items.browser', 'Za pomocą ustawień przeglądarki - większość przeglądarek pozwala na wyświetlanie i usuwanie plików cookie') }}</li>
              <li>{{ t('cookies.management.items.block', 'Blokowanie niektórych typów plików cookie (może to wpłynąć na funkcjonalność aplikacji)') }}</li>
              <li>{{ t('cookies.management.items.delete', 'Usuwanie plików cookie - możesz je usunąć w każdej chwili, jednak wymaga to ponownego logowania') }}</li>
            </ul>
            <p>
              {{ t('cookies.management.note', 'Uwaga: Wyłączenie niezbędnych plików cookie może spowodować, że niektóre funkcje aplikacji przestaną działać poprawnie.') }}
            </p>
          </div>
        </section>

        <section class="space-y-3">
          <h2 class="text-2xl font-semibold">
            {{ t('cookies.thirdParty.title', 'Pliki cookie osób trzecich') }}
          </h2>
          <p class="text-muted-foreground">
            {{ t('cookies.thirdParty.description', 'Aplikacja może wykorzystywać usługi zewnętrzne (np. Google Analytics, reCAPTCHA), które mogą umieszczać własne pliki cookie. Zgodnie z naszą polityką prywatności, informujemy o wykorzystaniu takich usług i zapewniamy odpowiednie zabezpieczenia danych.') }}
          </p>
        </section>

        <section class="space-y-3">
          <h2 class="text-2xl font-semibold">
            {{ t('cookies.privacy.title', 'Prywatność') }}
          </h2>
          <p class="text-muted-foreground">
            {{ t('cookies.privacy.description', 'Wszystkie pliki cookie używane przez aplikację służą wyłącznie do zapewnienia funkcjonalności serwisu. Nie używamy plików cookie do śledzenia użytkowników w celach marketingowych ani do przekazywania danych osobowych osobom trzecim bez Twojej zgody.') }}
          </p>
        </section>

        <section class="space-y-3">
          <h2 class="text-2xl font-semibold">
            {{ t('cookies.rodo.title', 'RODO') }}
          </h2>
          <p class="text-muted-foreground">
            {{ t('cookies.rodo.description', 'Zgodnie z Rozporządzeniem Ogólnym o Ochronie Danych (RODO), niezbędne pliki cookie nie wymagają Twojej zgody, ponieważ są niezbędne do świadczenia usługi. W przypadku innych plików cookie będziemy prosić o Twoją zgodę, jeśli będzie to wymagane.') }}
          </p>
        </section>
      </div>
    </div>
  </AuthenticatedLayout>
</template>

