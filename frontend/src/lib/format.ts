export function formatCropLabel(crop: string) {
  return crop.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

export function formatMass(grams: number) {
  if (grams >= 1000) return `${(grams / 1000).toFixed(1)} kg`
  return `${Math.round(grams)} g`
}

// A checkpoint instant as a short date, e.g. "3 Sept 2024". Rendered in UTC
// so the label matches the underlying timestamp rather than the viewer's
// clock; the full instant stays available via title attributes.
export function formatCheckpoint(iso: string) {
  return new Date(iso).toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    timeZone: 'UTC',
  })
}

// A sensor reading with its unit, or an em dash when the source has none.
export function formatReading(value: number | null | undefined, unit: string, fractionDigits = 1) {
  if (value === null || value === undefined) return '—'
  const number = value.toFixed(fractionDigits)
  return unit ? `${number} ${unit}` : number
}
