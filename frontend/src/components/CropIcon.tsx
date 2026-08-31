import type { CropType } from '../lib/crop'
import { cn } from '../lib/utils'

const SIZES = { sm: 12, md: 16, lg: 22, xl: 40 } as const

export function CropIcon({
  crop,
  size = 'md',
  className,
}: {
  crop: CropType
  size?: keyof typeof SIZES
  className?: string
}) {
  const px = SIZES[size]
  return (
    <svg
      width={px}
      height={px}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={cn('shrink-0', className)}
      role="img"
      aria-label={crop}
    >
      {crop === 'cucumber' ? (
        <>
          <path d="M6 18c6 2 12-4 10-10-6-2-12 4-10 10Z" />
          <path d="M10 14.5l1-1M13 12l1-1" />
        </>
      ) : crop === 'lettuce' ? (
        <>
          <path d="M12 20c-4 0-7-3-7-6 0-1 .5-2 1.5-2.5C6 9 8 7 10 7c1 0 1.6.4 2 1 .4-.6 1-1 2-1 2 0 4 2 3.5 4.5C18.5 12 19 13 19 14c0 3-3 6-7 6Z" />
        </>
      ) : (
        <>
          {/* tomato-family: stem + fruit cluster */}
          <path d="M12 8V4" />
          <path d="M12 5c-1.6-.2-2.7-1-3.2-2.2 1.7-.3 2.9.3 3.6 1.5" />
          <path d="M9.2 8.6c-.9-.5-1.9-.6-2.6-.2M14.8 8.6c.9-.5 1.9-.6 2.6-.2" />
          <circle cx="9" cy="14" r="3.4" />
          <circle cx="15.6" cy="16.4" r="2.6" />
        </>
      )}
    </svg>
  )
}
