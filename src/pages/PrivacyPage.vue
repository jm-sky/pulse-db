<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import HoverLink from '@/components/ui/hover-link/HoverLink.vue'
import AuthenticatedLayout from '@/layouts/AuthenticatedLayout.vue'
import { PublicRouteNames } from '@/router/publicRoutes'
import { config } from '@/shared/config/config'

const { t } = useI18n()
</script>

<template>
  <AuthenticatedLayout>
    <div class="space-y-6">
      <div class="space-y-2">
        <h1 class="text-3xl font-bold tracking-tight">
          {{ t('privacy.title', 'Polityka prywatności') }}
        </h1>
        <p class="text-muted-foreground">
          {{ t('privacy.subtitle', 'Jak chronimy Twoje dane') }}
        </p>
      </div>

      <div class="space-y-6">
        <section class="space-y-3">
          <h2 class="text-2xl font-semibold">
            {{ t('privacy.dataCollection.title', 'Zbieranie danych') }}
          </h2>
          <div class="space-y-2 text-muted-foreground">
            <p>
              {{ t('privacy.dataCollection.description', 'Aplikacja PulseDB zbiera następujące dane:') }}
            </p>
            <ul class="list-disc list-inside space-y-1">
              <li>{{ t('privacy.dataCollection.items.account', 'Dane konta: email, imię i nazwisko (wymagane do utworzenia konta)') }}</li>
              <li>{{ t('privacy.dataCollection.items.diagnostics', 'Dane diagnostyczne i wydajnościowe monitorowanych baz: historia zapytań, metryki i powiązane metadane (przechowywane w bazie PulseDB)') }}</li>
              <li>{{ t('privacy.dataCollection.items.settings', 'Ustawienia aplikacji: preferencje językowe i inne ustawienia') }}</li>
              <li>{{ t('privacy.dataCollection.items.usage', 'Dane użytkowania: logi dostępu, akcje podejmowane w aplikacji (w celu zapewnienia bezpieczeństwa i poprawy usługi)') }}</li>
            </ul>
          </div>
        </section>

        <section class="space-y-3">
          <h2 class="text-2xl font-semibold">
            {{ t('privacy.dataStorage.title', 'Przechowywanie danych') }}
          </h2>
          <p class="text-muted-foreground">
            {{ t('privacy.dataStorage.description', 'Wszystkie dane są przechowywane bezpiecznie na naszych serwerach w szyfrowanych bazach danych. Wykorzystujemy standardowe praktyki bezpieczeństwa, w tym hashowanie haseł, szyfrowanie połączeń (HTTPS) oraz regularne kopie zapasowe danych.') }}
          </p>
        </section>

        <section class="space-y-3">
          <h2 class="text-2xl font-semibold">
            {{ t('privacy.dataAccess.title', 'Dostęp do danych') }}
          </h2>
          <div class="space-y-2 text-muted-foreground">
            <p>
              {{ t('privacy.dataAccess.description', 'Twoje dane są dostępne tylko dla Ciebie i są chronione hasłem. Nasi administratorzy mają dostęp techniczny do danych wyłącznie w celach utrzymania i poprawy usługi, zgodnie z najlepszymi praktykami bezpieczeństwa.') }}
            </p>
            <p>
              {{ t('privacy.dataAccess.thirdParties', 'Nie udostępniamy Twoich danych osobowych osobom trzecim, z wyjątkiem przypadków wymaganych przez prawo lub z Twoją wyraźną zgodą.') }}
            </p>
          </div>
        </section>

        <section class="space-y-3">
          <h2 class="text-2xl font-semibold">
            {{ t('privacy.oauth.title', 'Uwierzytelnianie OAuth') }}
          </h2>
          <div class="space-y-2 text-muted-foreground">
            <p>
              {{ t('privacy.oauth.description', 'Oferujemy możliwość logowania się za pomocą zewnętrznych dostawców OAuth (Google, Facebook). Podczas korzystania z tej funkcji:') }}
            </p>
            <ul class="list-disc list-inside space-y-1">
              <li>{{ t('privacy.oauth.items.receive', 'Otrzymujemy podstawowe informacje z Twojego konta (email, imię, zdjęcie profilowe)') }}</li>
              <li>{{ t('privacy.oauth.items.store', 'Przechowujemy tylko niezbędne dane do świadczenia usługi') }}</li>
              <li>{{ t('privacy.oauth.items.share', 'Nie udostępniamy Twoich danych z powrotem dostawcom OAuth bez Twojej zgody') }}</li>
              <li>{{ t('privacy.oauth.items.revoke', 'Możesz w każdej chwili odwołać dostęp do swojego konta w ustawieniach dostawcy OAuth') }}</li>
            </ul>
            <p>
              {{ t('privacy.oauth.policies', 'Korzystając z OAuth, akceptujesz również politykę prywatności odpowiedniego dostawcy (Google lub Facebook).') }}
            </p>
          </div>
        </section>

        <section class="space-y-3">
          <h2 class="text-2xl font-semibold">
            {{ t('privacy.dataDeletion.title', 'Usuwanie danych') }}
          </h2>
          <div class="space-y-2 text-muted-foreground">
            <p>
              {{ t('privacy.dataDeletion.description', 'Masz pełną kontrolę nad swoimi danymi i możesz w każdej chwili je usunąć. Aby usunąć konto i wszystkie powiązane dane:') }}
            </p>
            <ol class="list-decimal list-inside space-y-1">
              <li>{{ t('privacy.dataDeletion.steps.settings', 'Przejdź do ustawień aplikacji') }}</li>
              <li>{{ t('privacy.dataDeletion.steps.delete', 'Znajdź sekcję "Usuń konto"') }}</li>
              <li>{{ t('privacy.dataDeletion.steps.confirm', 'Wpisz "DELETE" w polu potwierdzenia i potwierdź usunięcie') }}</li>
            </ol>
            <p>
              {{ t('privacy.dataDeletion.alternative', 'Alternatywnie, możesz skontaktować się z nami pod adresem') }}
              <a :href="`mailto:${config.contact.email}`" class="text-primary hover:underline">
                {{ config.contact.email }}
              </a>
              {{ t('privacy.dataDeletion.request', 'i poprosić o usunięcie konta.') }}
            </p>
            <p>
              {{ t('privacy.dataDeletion.retention', 'Po usunięciu konta, Twoje dane są usuwane z naszych systemów w ciągu 30 dni. Niektóre dane mogą być przechowywane dłużej, jeśli jest to wymagane przez prawo lub w celu rozwiązania sporów.') }}
            </p>
            <p>
              {{ t('privacy.dataDeletion.oauth', 'Jeśli używasz logowania OAuth, musisz również odwołać dostęp do aplikacji w ustawieniach swojego konta u dostawcy OAuth (Google/Facebook).') }}
            </p>
          </div>
        </section>

        <section class="space-y-3">
          <h2 class="text-2xl font-semibold">
            {{ t('privacy.userRights.title', 'Twoje prawa') }}
          </h2>
          <div class="space-y-2 text-muted-foreground">
            <p>
              {{ t('privacy.userRights.description', 'Zgodnie z RODO, masz prawo do:') }}
            </p>
            <ul class="list-disc list-inside space-y-1">
              <li>{{ t('privacy.userRights.access', 'Dostępu do swoich danych osobowych') }}</li>
              <li>{{ t('privacy.userRights.rectification', 'Sprawdzenia i poprawienia swoich danych') }}</li>
              <li>{{ t('privacy.userRights.erasure', 'Usunięcia swoich danych ("prawo do bycia zapomnianym")') }}</li>
              <li>{{ t('privacy.userRights.portability', 'Przeniesienia swoich danych do innej usługi') }}</li>
              <li>{{ t('privacy.userRights.object', 'Sprzeciwu wobec przetwarzania danych') }}</li>
            </ul>
            <p>
              {{ t('privacy.userRights.contact', 'Aby skorzystać z któregokolwiek z tych praw, skontaktuj się z nami pod adresem') }}
              <a :href="`mailto:${config.contact.email}`" class="text-primary hover:underline">
                {{ config.contact.email }}
              </a>.
            </p>
          </div>
        </section>

        <section class="space-y-3">
          <h2 class="text-2xl font-semibold">
            {{ t('privacy.cookies.title', 'Pliki cookie') }}
          </h2>
          <p class="text-muted-foreground">
            {{ t('privacy.cookies.description', 'Aplikacja wykorzystuje pliki cookie do utrzymania sesji użytkownika i poprawy funkcjonalności. Więcej informacji na temat wykorzystania plików cookie można znaleźć na stronie') }}
            <HoverLink :to="{ name: PublicRouteNames.cookies }">
              {{ t('privacy.cookies.link', 'Informacja o ciasteczkach') }}
            </HoverLink>.
          </p>
        </section>

        <section class="space-y-3">
          <h2 class="text-2xl font-semibold">
            {{ t('privacy.changes.title', 'Zmiany w polityce') }}
          </h2>
          <p class="text-muted-foreground">
            {{ t('privacy.changes.description', 'W przypadku wprowadzenia istotnych zmian w sposobie przetwarzania danych, ta strona zostanie zaktualizowana, a użytkownicy zostaną poinformowani o zmianach za pośrednictwem emaila lub powiadomienia w aplikacji. Kontynuowanie korzystania z aplikacji po wprowadzeniu zmian oznacza akceptację zaktualizowanej polityki prywatności.') }}
          </p>
        </section>

        <section class="space-y-3">
          <h2 class="text-2xl font-semibold">
            {{ t('privacy.contact.title', 'Kontakt') }}
          </h2>
          <p class="text-muted-foreground">
            {{ t('privacy.contact.description', 'W przypadku pytań dotyczących polityki prywatności lub przetwarzania danych, prosimy o kontakt:') }}
          </p>
          <p class="text-muted-foreground">
            <a :href="`mailto:${config.contact.email}`" class="text-primary hover:underline">
              {{ config.contact.email }}
            </a>
          </p>
        </section>
      </div>
    </div>
  </AuthenticatedLayout>
</template>

