// modules/settings/validation/settings.schema.ts
import { z } from 'zod'

export const settingsSchema = z.object({
  darkMode: z.enum(['light', 'dark']),
  locale: z.enum(['en', 'pl']),
  profilePublic: z.boolean().optional(),
  emailPublic: z.boolean().optional(),
  imageProcessingMode: z.enum(['high_quality', 'balanced', 'storage_saver']).optional().nullable(),
})

export type SettingsFormData = z.infer<typeof settingsSchema>


