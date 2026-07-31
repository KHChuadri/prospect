'use client'

import { useParams, useRouter } from 'next/navigation'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { ApplicationForm } from '@/components/applications/ApplicationForm'
import { useApplication } from '@/hooks/useApplication'
import { useUpdateApplication } from '@/hooks/useApplications'

export default function EditApplicationPage() {
  const { id } = useParams<{ id: string }>()
  const appId = Number(id)
  const router = useRouter()

  const { data: app, isLoading } = useApplication(appId)
  const updateApp = useUpdateApplication(appId)

  if (isLoading) return (
    <div className="mx-auto max-w-lg space-y-4">
      <div className="h-8 w-40 animate-pulse rounded-md bg-muted" />
      <div className="h-64 animate-pulse rounded-md bg-muted" />
    </div>
  )
  if (!app) return <p className="text-destructive">Application not found.</p>

  return (
    <div className="mx-auto max-w-lg">
      <Card>
        <CardHeader><CardTitle>Edit application</CardTitle></CardHeader>
        <CardContent>
          <ApplicationForm
            defaultValues={{
              company:     app.company,
              role:        app.role,
              source:      app.source ?? '',
              salaryRange: app.salaryRange ?? '',
            }}
            onSubmit={(data) => updateApp.mutateAsync(data).then(() => {})}
            onSuccess={() => router.push(`/applications/${appId}`)}
            submitLabel="Save changes"
          />
        </CardContent>
      </Card>
    </div>
  )
}
