import type { ReactNode } from 'react'

export function AuthPageFrame({ eyebrow, title, description, children }: { eyebrow: string; title: string; description: string; children: ReactNode }) {
  return (
    <div className="mx-auto max-w-lg py-3 sm:py-7">
      <div className="mb-8 text-center">
        <p className="text-xs font-bold uppercase tracking-[0.16em] text-accent dark:text-blue-300">{eyebrow}</p>
        <h1 className="mt-3 text-3xl font-extrabold tracking-tight sm:text-4xl">{title}</h1>
        <p className="mt-3 text-sm leading-7 text-muted dark:text-slate-300">{description}</p>
      </div>
      <div className="panel p-6 sm:p-9">{children}</div>
    </div>
  )
}
