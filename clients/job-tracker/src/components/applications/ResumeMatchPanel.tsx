'use client'

import { useState } from 'react'
import { AxiosError } from 'axios'
import Link from 'next/link'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Textarea } from '@/components/ui/textarea'
import { useMatch, useOptimize } from '@/hooks/useAi'
import type { MatchResult } from '@/lib/types'

// The agent returns 409 with a detail string when a prerequisite is missing.
// "no job description stored…" means the app has no JD; anything else means no résumé.
function prereqMessage(err: unknown): string | null {
  if (err instanceof AxiosError && err.response?.status === 409) {
    const detail = String(err.response.data?.detail ?? '').toLowerCase()
    return detail.includes('job description')
      ? 'No job description stored for this application. Add one by pasting a JD when creating the application.'
      : 'Upload your résumé first.'
  }
  return null
}

export function ResumeMatchPanel({ appId }: { appId: number }) {
  const match = useMatch(appId)
  const optimize = useOptimize(appId)
  const [result, setResult] = useState<MatchResult | null>(null)
  const [optimized, setOptimized] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const runMatch = async () => {
    setNotice(null)
    try {
      setResult(await match.mutateAsync(undefined))
    } catch (err) {
      setResult(null)
      setNotice(prereqMessage(err) ?? 'Analysis failed — try again.')
    }
  }

  const runOptimize = async () => {
    setNotice(null)
    try {
      setOptimized(await optimize.mutateAsync(undefined))
    } catch (err) {
      setOptimized(null)
      setNotice(prereqMessage(err) ?? 'Optimization failed — try again.')
    }
  }

  return (
    <Card>
      <CardHeader><CardTitle className="text-base">Résumé match</CardTitle></CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap gap-2">
          <Button size="sm" onClick={runMatch} disabled={match.isPending}>
            {match.isPending ? 'Analyzing…' : 'Analyze match'}
          </Button>
          <Button size="sm" variant="outline" onClick={runOptimize} disabled={optimize.isPending}>
            {optimize.isPending ? 'Optimizing…' : 'Optimize résumé'}
          </Button>
        </div>

        {notice && (
          <p className="text-sm text-muted-foreground">
            {notice}{' '}
            {notice.startsWith('Upload') && (
              <Link href="/resume" className="underline">Go to résumé</Link>
            )}
          </p>
        )}

        {result && (
          <div className="space-y-3 text-sm">
            <p className="text-lg font-semibold">Fit score: {result.score}/100</p>
            {result.matched.length > 0 && (
              <div>
                <p className="text-xs uppercase tracking-wide text-muted-foreground">Matched</p>
                <div className="mt-1 flex flex-wrap gap-1">
                  {result.matched.map((m) => <Badge key={m} variant="secondary">{m}</Badge>)}
                </div>
              </div>
            )}
            {result.missing.length > 0 && (
              <div>
                <p className="text-xs uppercase tracking-wide text-muted-foreground">Missing</p>
                <div className="mt-1 flex flex-wrap gap-1">
                  {result.missing.map((m) => <Badge key={m} variant="outline">{m}</Badge>)}
                </div>
              </div>
            )}
            {result.suggestions.length > 0 && (
              <ul className="list-disc pl-5 text-muted-foreground">
                {result.suggestions.map((s, i) => <li key={i}>{s}</li>)}
              </ul>
            )}
          </div>
        )}

        {optimized && (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <p className="text-xs uppercase tracking-wide text-muted-foreground">Tailored résumé</p>
              <Button size="sm" variant="ghost" onClick={() => navigator.clipboard?.writeText(optimized)}>
                Copy
              </Button>
            </div>
            <Textarea readOnly value={optimized} rows={16} />
          </div>
        )}
      </CardContent>
    </Card>
  )
}
