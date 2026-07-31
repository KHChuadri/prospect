'use client'

import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import {
  useRecommendations,
  useAcceptRecommendation,
  useDismissRecommendation,
} from '@/hooks/useRecommendations'

export default function RecommendationsPage() {
  const { data: recs, isLoading } = useRecommendations()
  const accept = useAcceptRecommendation()
  const dismiss = useDismissRecommendation()
  const busy = accept.isPending || dismiss.isPending

  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <div>
        <h1 className="text-lg font-semibold">Recommendations</h1>
        <p className="text-sm text-muted-foreground">
          Jobs parsed from your email alerts. Accept to add to your board, or dismiss.
        </p>
      </div>

      {isLoading && <p className="text-sm text-muted-foreground">Loading…</p>}
      {!isLoading && (recs?.length ?? 0) === 0 && (
        <p className="text-sm text-muted-foreground">No recommendations right now.</p>
      )}

      {recs?.map((rec) => (
        <Card key={rec.id}>
          <CardHeader>
            <CardTitle className="text-base">
              {rec.role} · <span>{rec.company}</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="text-sm text-muted-foreground">
              {rec.location && <span>{rec.location} · </span>}
              <span>from {rec.source_sender}</span>
            </div>
            {rec.url && (
              <a href={rec.url} target="_blank" rel="noreferrer"
                 className="text-sm text-primary underline">
                View posting
              </a>
            )}
            <p className="text-sm text-muted-foreground line-clamp-3">{rec.raw_snippet}</p>
            <div className="flex gap-3">
              <Button onClick={() => accept.mutate(rec)} disabled={busy}>
                {accept.isPending ? 'Adding…' : 'Accept'}
              </Button>
              <Button variant="ghost" onClick={() => dismiss.mutate(rec.id)} disabled={busy}>
                Dismiss
              </Button>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
