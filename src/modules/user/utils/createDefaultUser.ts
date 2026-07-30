import type { IUser } from '../types/user.types'
import { generateUUID } from './generateUUID'

export const createDefaultUser = (): IUser => {
  const now = new Date().toISOString()
  return {
    id: generateUUID(),
    name: 'User',
    email: 'user@example.com',
    createdAt: now,
    updatedAt: now,
  }
}
