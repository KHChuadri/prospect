'use client'

import { useEffect } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import Link from 'next/link'
import Image from 'next/image'
import { isAuthenticated, clearTokens } from '@/lib/auth'
import { authApi } from '@/lib/api'
import { Button } from '@/components/ui/button'

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const pathname = usePathname()
  const navLinks = [
    { href: '/', label: 'Board' },
    { href: '/analytics', label: 'Analytics' },
    { href: '/follow-ups', label: 'Follow-ups' },
    { href: '/resume', label: 'Résumé' },
    { href: '/recommendations', label: 'Recommendations' },
    { href: '/events', label: 'Events' },
  ]

  useEffect(() => {
    if (!isAuthenticated()) router.replace('/login')
  }, [router])

  const handleLogout = async () => {
    try { await authApi.revoke() } catch { /* revoke is best-effort */ }
    clearTokens()
    router.push('/login')
  }

  return (
    <div className="min-h-screen">
      <header className="glass sticky top-0 z-10 border-b border-border">
        <div className="container mx-auto flex h-14 items-center justify-between px-4">
          <div className="flex items-center gap-6">
            <Link href="/" className="flex items-center gap-2" aria-label="Prospect — home">
              {/* Reversed mark: the app is dark-only (see globals.css), and the
                  kit forbids recolouring, so this is the variant drawn for dark
                  grounds rather than the two-colour on-light one. */}
              <Image
                src="/brand/prospect-mark.svg"
                alt=""
                width={22}
                height={22}
                priority
                aria-hidden
              />
              <span className="font-wordmark text-base font-semibold tracking-[-0.035em]">
                Prospect
              </span>
            </Link>
            <nav className="flex items-center gap-1">
              {navLinks.map((link) => {
                const active =
                  link.href === '/' ? pathname === '/' : pathname.startsWith(link.href)
                return (
                  <Link
                    key={link.href}
                    href={link.href}
                    className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                      active
                        ? 'bg-primary/15 text-foreground ring-1 ring-primary/30'
                        : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                    }`}
                  >
                    {link.label}
                  </Link>
                )
              })}
            </nav>
          </div>
          <Button variant="ghost" size="sm" onClick={handleLogout}>
            Sign out
          </Button>
        </div>
      </header>
      <main className="container mx-auto px-4 py-6">{children}</main>
    </div>
  )
}
