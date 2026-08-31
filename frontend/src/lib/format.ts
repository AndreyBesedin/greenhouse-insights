export function formatCropLabel(crop: string) {
  return crop.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}
