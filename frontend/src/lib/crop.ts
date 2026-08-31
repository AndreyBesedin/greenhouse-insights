export type CropType = 'vine-tomato' | 'cherry-tomato' | 'cucumber' | 'pepper' | 'lettuce'

/** Maps a free-text crop/variety string (e.g. from the API) to an icon variant. */
export function cropIconVariant(crop: string): CropType {
  const normalized = crop.toLowerCase()
  if (normalized.includes('cucumber')) return 'cucumber'
  if (normalized.includes('lettuce')) return 'lettuce'
  if (normalized.includes('pepper')) return 'pepper'
  if (normalized.includes('cherry')) return 'cherry-tomato'
  return 'vine-tomato'
}
