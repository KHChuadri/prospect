'use client'

import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { useApplication } from '@/hooks/useApplication'
import { useNotes } from '@/hooks/useNotes'
import { useDeleteApplication, useUpdateStatus } from '@/hooks/useApplications'
import { StatusBadge } from '@/components/applications/StatusBadge'
import { ResumeMatchPanel } from '@/components/applications/ResumeMatchPanel'
import { NotesList } from '@/components/notes/NotesList'
import { AddNoteForm } from '@/components/notes/AddNoteForm'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import { APPLICATION_STATUSES, type ApplicationStatus } from '@/lib/types'

export default function ApplicationDetailPage() {
  const { id } = useParams<{ id: string }>()
  const appId = Number(id)
  const router = useRouter()

  const { data: app, isLoading } = useApplication(appId)
  const { data: notes = [] } = useNotes(appId)
  const updateStatus = useUpdateStatus(appId)
  const deleteApp = useDeleteApplication()

  if (isLoading) return (
    <div className="space-y-4">
      <div className="h-8 w-48 animate-pulse rounded-md bg-muted" />
      <div className="h-4 w-32 animate-pulse rounded-md bg-muted" />
      <div className="h-40 animate-pulse rounded-md bg-muted" />
    </div>
  )
  if (!app) return <p className="text-destructive">Application not found.</p>

  const handleDelete = async () => {
    if (!confirm('Delete this application?')) return
    await deleteApp.mutateAsync(appId)
    router.push('/')
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold">{app.company}</h1>
          <p className="text-muted-foreground">{app.role}</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" nativeButton={false} render={<Link href={`/applications/${appId}/edit`} />}>
            Edit
          </Button>
          <Button variant="destructive" size="sm" onClick={handleDelete}>
            Delete
          </Button>
        </div>
      </div>

      <Card>
        <CardContent className="grid gap-4 pt-6 sm:grid-cols-2">
          <div>
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Status</p>
            <div className="mt-1 flex items-center gap-2">
              <StatusBadge status={app.status} />
              <Select
                value={app.status}
                onValueChange={(v) => updateStatus.mutate(v as ApplicationStatus)}
              >
                <SelectTrigger className="h-7 w-auto text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {APPLICATION_STATUSES.map((s) => (
                    <SelectItem key={s} value={s}>{s}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <div>
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Applied</p>
            <p className="mt-1 text-sm">{new Date(app.appliedAt).toLocaleDateString()}</p>
          </div>
          {app.source && (
            <div>
              <p className="text-xs uppercase tracking-wide text-muted-foreground">Source</p>
              <p className="mt-1 text-sm">{app.source}</p>
            </div>
          )}
          {app.salaryRange && (
            <div>
              <p className="text-xs uppercase tracking-wide text-muted-foreground">Salary range</p>
              <p className="mt-1 text-sm">{app.salaryRange}</p>
            </div>
          )}
        </CardContent>
      </Card>

      {app.statusTransitions.length > 0 && (
        <Card>
          <CardHeader><CardTitle className="text-base">Status history</CardTitle></CardHeader>
          <CardContent>
            <ul className="space-y-2 text-sm">
              {app.statusTransitions.map((t) => (
                <li key={t.id} className="flex items-center gap-2">
                  <StatusBadge status={t.fromStatus} />
                  <span className="text-muted-foreground">→</span>
                  <StatusBadge status={t.toStatus} />
                  <span className="ml-auto text-xs text-muted-foreground">
                    {new Date(t.transitionedAt).toLocaleString()}
                  </span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      <ResumeMatchPanel appId={appId} />

      <Card>
        <CardHeader><CardTitle className="text-base">Notes</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <NotesList notes={notes} />
          <Separator />
          <AddNoteForm applicationId={appId} />
        </CardContent>
      </Card>
    </div>
  )
}
