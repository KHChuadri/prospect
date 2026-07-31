'use client'

import { useState } from 'react'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import {
  useEvents,
  useMarkInterested,
  useDismissEvent,
  useUndoEventDecision,
} from '@/hooks/useEvents'
import type { EventItem } from '@/lib/types'

function formatWhen(e: EventItem) {
  if (!e.starts_at) return 'Date TBC'
  return new Date(e.starts_at).toLocaleString(undefined, {
    weekday: 'short', day: 'numeric', month: 'short',
    hour: '2-digit', minute: '2-digit',
  })
}

function EventCard({ event, saved }: { event: EventItem; saved: boolean }) {
  const interested = useMarkInterested()
  const dismiss = useDismissEvent()
  const undo = useUndoEventDecision()
  const busy = interested.isPending || dismiss.isPending || undo.isPending

  // Prospect cannot take registrations — that always happens on the source
  // site. So the primary button does both: records the decision and opens the
  // page. A button that only flips a status column is a dead end.
  const register = () => {
    window.open(event.url, '_blank', 'noreferrer')
    interested.mutate(event.id)
  }

  return (
    <Card className={event.company_match ? 'border-primary' : undefined}>
      <CardHeader>
        <CardTitle className="flex items-start justify-between gap-3 text-base">
          <span>{event.title}</span>
          <span className="shrink-0 rounded bg-muted px-2 py-0.5 text-[10px] uppercase tracking-wide text-muted-foreground">
            {event.status === 'interested' ? 'Interested' : event.event_type.replace('_', ' ')}
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="text-sm text-muted-foreground">
          <span className={event.starts_at ? undefined : 'text-amber-600'}>
            {formatWhen(event)}
          </span>
          {event.is_online && <span> · Online</span>}
          {event.location && <span> · {event.location}</span>}
        </div>

        {(event.organizations.length > 0 || event.topics.length > 0) && (
          <div className="flex flex-wrap gap-1.5">
            {[...event.organizations, ...event.topics].map((tag) => (
              <span key={tag} className="rounded-full border px-2 py-0.5 text-[11px] text-muted-foreground">
                {tag}
              </span>
            ))}
          </div>
        )}

        {event.company_match && (
          <p className="text-xs font-medium text-primary">
            ★ You have an application with one of these companies
          </p>
        )}

        {event.description && (
          <p className="line-clamp-3 text-sm text-muted-foreground">{event.description}</p>
        )}

        <div className="flex items-center gap-3">
          {saved || event.status === 'interested' ? (
            <>
              <Button onClick={() => window.open(event.url, '_blank', 'noreferrer')}>
                Open page ↗
              </Button>
              <Button variant="ghost" disabled={busy} onClick={() => undo.mutate(event.id)}>
                Undo
              </Button>
            </>
          ) : (
            <>
              <Button disabled={busy} onClick={register}>Register ↗</Button>
              <Button variant="ghost" disabled={busy} onClick={() => dismiss.mutate(event.id)}>
                Not interested
              </Button>
            </>
          )}
          <span className="ml-auto text-[11px] text-muted-foreground">{event.source_name}</span>
        </div>
      </CardContent>
    </Card>
  )
}

export default function EventsPage() {
  const [saved, setSaved] = useState(false)
  const [onlyMatches, setOnlyMatches] = useState(false)
  const { data: events, isLoading } = useEvents(saved)

  // Filtering happens here, not at crawl time — so a filter can never
  // silently lose an event, and changing your mind costs no re-crawl.
  const visible = (events ?? []).filter((e) => !onlyMatches || e.company_match)

  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <div>
        <h1 className="text-lg font-semibold">Events</h1>
        <p className="text-sm text-muted-foreground">
          Networking events, panels and careers fairs found across your sources.
          Registration happens on the event&apos;s own site.
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        <Button size="sm" variant={saved ? 'ghost' : 'default'} onClick={() => setSaved(false)}>
          Upcoming
        </Button>
        <Button size="sm" variant={saved ? 'default' : 'ghost'} onClick={() => setSaved(true)}>
          Saved
        </Button>
        <Button
          size="sm"
          variant={onlyMatches ? 'default' : 'ghost'}
          onClick={() => setOnlyMatches((v) => !v)}
        >
          My companies
        </Button>
      </div>

      {isLoading && <p className="text-sm text-muted-foreground">Loading…</p>}
      {!isLoading && visible.length === 0 && (
        <p className="text-sm text-muted-foreground">
          {saved ? 'Nothing saved yet.' : 'No upcoming events right now.'}
        </p>
      )}

      {visible.map((event) => (
        <EventCard key={event.id} event={event} saved={saved} />
      ))}
    </div>
  )
}
