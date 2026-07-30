/**
 * Polish pluralization rule for vue-i18n
 * Returns index for plural form based on count
 *
 * Forms:
 * - 0: zero form (0 przedmiotów)
 * - 1: singular (1 przedmiot)
 * - 2: few (2-4, 22-24, 32-34 przedmioty)
 * - 3: many (5-21, 25-31, etc. przedmiotów)
 */
export function getPolishPluralizationRule(choice: number): number {
  // Handle zero
  if (choice === 0) {
    return 0
  }

  // Handle one (singular)
  if (choice === 1) {
    return 1
  }

  // Check if number is in "teen" range (11-19)
  const isTeen = choice > 10 && choice < 20

  // Check if number ends with 2, 3, or 4
  const endsWithTwoToFour = choice % 10 >= 2 && choice % 10 <= 4

  // Handle few: 2-4, 22-24, 32-34, etc. (but NOT 12-14)
  if (!isTeen && endsWithTwoToFour) {
    return 2
  }

  // Handle many: everything else (5-10, 11-21, 25-31, etc.)
  return 3
}
