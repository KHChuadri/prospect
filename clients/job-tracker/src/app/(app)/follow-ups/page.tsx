'use client'

import { useState } from 'react'
import { useFollowups, useApproveFollowup, useRejectFollowup } from '@/hooks/useFollowups'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'

export default function FollowUpsPage() {
  const { data: items = [], isLoading } = useFollowups('pending')
  const approve = useApproveFollowup()
  const reject = useRejectFollowup()
  const [drafts, setDrafts] = useState<Record<number, { to: string; subject: string; body: string }>>({})

  function field(id: number, init: { subject: string; body: string }) {
    return drafts[id] ?? { to: '', subject: init.subject, body: init.body }
  }
  function set(
    id: number,
    init: { subject: string; body: string },
    patch: Partial<{ to: string; subject: string; body: string }>,
  ) {
    setDrafts((d) => ({ ...d, [id]: { ...field(id, init), ...patch } }))
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Follow-ups</h1>
      {isLoading ? (
        <div className="h-24 animate-pulse rounded-xl bg-muted" />
      ) : items.length === 0 ? (
        <p className="text-muted-foreground">No pending follow-ups.</p>
      ) : (
        <ul className="space-y-4">
          {items.map((f) => {
            const d = field(f.id, { subject: f.draft_subject, body: f.draft_body })
            return (
              <li key={f.id} className="rounded-xl border p-4 space-y-3">
                <p className="text-sm text-muted-foreground">{f.reason}</p>
                <Input value={d.to} placeholder="recipient@company.com"
                       onChange={(e) => set(f.id, { subject: f.draft_subject, body: f.draft_body }, { to: e.target.value })} />
                <Input value={d.subject}
                       onChange={(e) => set(f.id, { subject: f.draft_subject, body: f.draft_body }, { subject: e.target.value })} />
                <Textarea value={d.body} rows={6}
                          onChange={(e) => set(f.id, { subject: f.draft_subject, body: f.draft_body }, { body: e.target.value })} />
                <div className="flex gap-2">
                  <Button
                    disabled={!d.to || approve.isPending}
                    onClick={() => approve.mutate({ id: f.id, recipientEmail: d.to,
                                                    subject: d.subject, body: d.body })}>
                    Approve & send
                  </Button>
                  <Button variant="outline" disabled={reject.isPending}
                          onClick={() => reject.mutate(f.id)}>
                    Reject
                  </Button>
                </div>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
