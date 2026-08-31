export function formatCropLabel(crop: string) {
  return crop.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

export function formatMass(grams: number) {
  if (grams >= 1000) return `${(grams / 1000).toFixed(1)} kg`
  return `${Math.round(grams)} g`
}
