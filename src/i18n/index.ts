// Application i18n configuration
// This file merges registry messages with module-specific messages
// and creates the i18n instance for your application.

import { adminEn, adminPl } from '@/modules/admin/i18n'
import { authEn, authPl } from '@/modules/auth/i18n'
import { settingsEn, settingsPl } from '@/modules/settings/i18n'
import { userEn, userPl } from '@/modules/user/i18n'
import { createI18nInstance } from '@/shared/i18n'
import registryEn from '@/shared/i18n/locales/en'
import registryPl from '@/shared/i18n/locales/pl'

const en = {
  ...registryEn,
  ...adminEn,
  ...authEn,
  ...settingsEn,
  ...userEn,
}
const pl = {
  ...registryPl,
  ...adminPl,
  ...authPl,
  ...settingsPl,
  ...userPl,
}

export type Messages = typeof en

export const i18n = createI18nInstance({
  messages: {
    en,
    pl,
  },
})
