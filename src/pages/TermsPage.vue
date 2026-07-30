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
          {{ t('terms.title', 'Regulamin') }}
        </h1>
        <p class="text-muted-foreground">
          {{ t('terms.subtitle', 'Warunki korzystania z serwisu') }}
        </p>
      </div>

      <div class="space-y-6">
        <section class="space-y-3">
          <h2 class="text-2xl font-semibold">
            {{ t('terms.acceptance.title', 'Akceptacja warunków') }}
          </h2>
          <p class="text-muted-foreground">
            {{ t('terms.acceptance.description', 'Korzystając z aplikacji PulseDB, akceptujesz niniejsze warunki korzystania. Jeśli nie zgadzasz się z którymkolwiek z poniższych warunków, nie powinieneś korzystać z serwisu.') }}
          </p>
        </section>

        <section class="space-y-3">
          <h2 class="text-2xl font-semibold">
            {{ t('terms.account.title', 'Konto użytkownika') }}
          </h2>
          <div class="space-y-2 text-muted-foreground">
            <p>
              {{ t('terms.account.description', 'Aby korzystać z niektórych funkcji aplikacji, musisz utworzyć konto. Zobowiązujesz się do:') }}
            </p>
            <ul class="list-disc list-inside space-y-1">
              <li>{{ t('terms.account.responsibilities.provide', 'Podawania prawdziwych i aktualnych informacji podczas rejestracji') }}</li>
              <li>{{ t('terms.account.responsibilities.maintain', 'Utrzymywania bezpieczeństwa swojego konta i hasła') }}</li>
              <li>{{ t('terms.account.responsibilities.notify', 'Niezwłocznego powiadamiania nas o każdym nieuprawnionym użyciu Twojego konta') }}</li>
              <li>{{ t('terms.account.responsibilities.responsible', 'Odpowiedzialności za wszystkie działania podejmowane przy użyciu Twojego konta') }}</li>
            </ul>
          </div>
        </section>

        <section class="space-y-3">
          <h2 class="text-2xl font-semibold">
            {{ t('terms.oauth.title', 'Uwierzytelnianie OAuth') }}
          </h2>
          <div class="space-y-2 text-muted-foreground">
            <p>
              {{ t('terms.oauth.description', 'Aplikacja umożliwia logowanie się za pomocą zewnętrznych dostawców OAuth (np. Google, Facebook). Korzystając z tej funkcji:') }}
            </p>
            <ul class="list-disc list-inside space-y-1">
              <li>{{ t('terms.oauth.rules.provider', 'Akceptujesz warunki użytkowania i politykę prywatności dostawcy OAuth') }}</li>
              <li>{{ t('terms.oauth.rules.data', 'Wyrażasz zgodę na udostępnienie nam podstawowych informacji z Twojego konta (email, imię, zdjęcie profilowe)') }}</li>
              <li>{{ t('terms.oauth.rules.revoke', 'Możesz w każdej chwili odwołać dostęp do swojego konta w ustawieniach dostawcy OAuth') }}</li>
            </ul>
          </div>
        </section>

        <section class="space-y-3">
          <h2 class="text-2xl font-semibold">
            {{ t('terms.content.title', 'Zawartość użytkownika') }}
          </h2>
          <p class="text-muted-foreground">
            {{ t('terms.content.description', 'Użytkownik zachowuje pełne prawa do treści, które tworzy i przechowuje w aplikacji. Użytkownik przyznaje nam jedynie niezbędną licencję do przechowywania, wyświetlania i przetwarzania tych danych w celu świadczenia usługi.') }}
          </p>
        </section>

        <section class="space-y-3">
          <h2 class="text-2xl font-semibold">
            {{ t('terms.prohibited.title', 'Zakazane działania') }}
          </h2>
          <div class="space-y-2 text-muted-foreground">
            <p>
              {{ t('terms.prohibited.description', 'Zabrania się:') }}
            </p>
            <ul class="list-disc list-inside space-y-1">
              <li>{{ t('terms.prohibited.items.illegal', 'Używania aplikacji do celów niezgodnych z prawem') }}</li>
              <li>{{ t('terms.prohibited.items.harmful', 'Przesyłania treści szkodliwych, obraźliwych lub niezgodnych z prawem') }}</li>
              <li>{{ t('terms.prohibited.items.access', 'Próby nieuprawnionego dostępu do systemu lub innych kont użytkowników') }}</li>
              <li>{{ t('terms.prohibited.items.disrupt', 'Zakłócania działania aplikacji lub serwerów') }}</li>
              <li>{{ t('terms.prohibited.items.impersonate', 'Udawania innej osoby lub podawania się za kogoś innego') }}</li>
            </ul>
          </div>
        </section>

        <section class="space-y-3">
          <h2 class="text-2xl font-semibold">
            {{ t('terms.termination.title', 'Zakończenie konta') }}
          </h2>
          <p class="text-muted-foreground">
            {{ t('terms.termination.description', 'Zastrzegamy sobie prawo do zawieszenia lub usunięcia Twojego konta w przypadku naruszenia niniejszych warunków lub z innych ważnych przyczyn. Możesz również w każdej chwili usunąć swoje konto w ustawieniach aplikacji.') }}
          </p>
        </section>

        <section class="space-y-3">
          <h2 class="text-2xl font-semibold">
            {{ t('terms.disclaimer.title', 'Wyłączenie odpowiedzialności') }}
          </h2>
          <p class="text-muted-foreground">
            {{ t('terms.disclaimer.description', 'Aplikacja jest świadczona "tak, jak jest", bez jakichkolwiek gwarancji. Nie ponosimy odpowiedzialności za jakiekolwiek szkody wynikające z korzystania z aplikacji.') }}
          </p>
        </section>

        <section class="space-y-3">
          <h2 class="text-2xl font-semibold">
            {{ t('terms.changes.title', 'Zmiany w regulaminie') }}
          </h2>
          <p class="text-muted-foreground">
            {{ t('terms.changes.description', 'Zastrzegamy sobie prawo do wprowadzania zmian w niniejszym regulaminie. O istotnych zmianach poinformujemy użytkowników. Kontynuowanie korzystania z aplikacji po wprowadzeniu zmian oznacza akceptację nowych warunków.') }}
          </p>
        </section>

        <section class="space-y-3">
          <h2 class="text-2xl font-semibold">
            {{ t('terms.contact.title', 'Kontakt') }}
          </h2>
          <p class="text-muted-foreground">
            {{ t('terms.contact.description', 'W przypadku pytań dotyczących niniejszego regulaminu, prosimy o kontakt za pomocą formularza kontaktowego dostępnego w aplikacji.') }}
          </p>
        </section>
      </div>
    </div>
  </AuthenticatedLayout>
</template>


