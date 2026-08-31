import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'

import { CropIcon } from './CropIcon'

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-ink font-sans text-paper">
      <header className="border-b border-white/[0.06]">
        <div className="mx-auto flex h-14 max-w-[1440px] items-center gap-8 px-6">
          <Link to="/" className="flex items-center gap-2.5">
            <span className="grid size-7 place-items-center rounded-md bg-brand/15 text-brand outline-1 -outline-offset-1 outline-brand/30">
              <CropIcon crop="cherry-tomato" size="sm" />
            </span>
            <span className="font-display text-[15px] font-semibold tracking-tight">
              Greenhouse Insights
            </span>
          </Link>
          <nav className="hidden items-center gap-1 text-sm md:flex">
            <Link to="/" className="rounded-md px-3 py-1.5 font-medium text-paper">
              Greenhouses
            </Link>
          </nav>
          <div className="ml-auto flex items-center gap-3">
            <Link
              to="/login"
              className="grid size-8 place-items-center rounded-full bg-ink-700 text-xs font-medium text-paper outline-1 -outline-offset-1 outline-white/10"
              title="Sign out"
            >
              GI
            </Link>
          </div>
        </div>
      </header>
      {children}
      <footer className="border-t border-white/[0.06]">
        <div className="mx-auto flex max-w-[1440px] items-center justify-between px-6 py-6 text-xs text-mist">
          <span>Greenhouse Insights</span>
          <span>Operator console</span>
        </div>
      </footer>
    </div>
  )
}
