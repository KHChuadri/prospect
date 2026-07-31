'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Textarea } from '@/components/ui/textarea'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ApplicationForm } from '@/components/applications/ApplicationForm'
import { useCreateApplication } from '@/hooks/useApplications'
import { useExtract } from '@/hooks/useAi'
import { aiApi } from '@/lib/api'
import type { Extraction } from '@/lib/types'

export default function NewApplicationPage() {
  const router = useRouter()
  const createApp = useCreateApplication()
  const extract = useExtract()

  const [jdText, setJdText] = useState('')
  const [extracted, setExtracted] = useState<Extraction | null>(null)
  const [extractError, setExtractError] = useState<string | null>(null)
  const [seedKey, setSeedKey] = useState(0)

  const handleExtract = async () => {
    setExtractError(null)
    try {
      const data = await extract.mutateAsync(jdText)
      if (!data.ok) {
        setExtractError("Couldn't read this as a job description — fill the form manually.")
        return
      }
      setExtracted(data)
      setSeedKey((k) => k + 1) // remount the form so it picks up the new defaults
    } catch {
      setExtractError('Extraction failed — fill the form manually.')
    }
  }

  const aiFilled = extracted
    ? ['company', 'role', ...(extracted.salary ? ['salaryRange'] : [])]
    : []

  const defaultValues = extracted
    ? { company: extracted.company, role: extracted.role, salaryRange: extracted.salary ?? '' }
    : undefined

  return (
    <div className="mx-auto max-w-lg space-y-4">
      <Card>
        <CardHeader><CardTitle>Paste a job description</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          <Textarea
            value={jdText}
            onChange={(e) => setJdText(e.target.value)}
            rows={6}
            placeholder="Paste the job description here to auto-fill the form…"
          />
          <Button
            type="button"
            variant="outline"
            onClick={handleExtract}
            disabled={extract.isPending || jdText.trim().length === 0}
          >
            {extract.isPending ? 'Extracting…' : 'Extract'}
          </Button>
          {extractError && <p className="text-sm text-destructive">{extractError}</p>}
          {extracted && (extracted.location || extracted.requirements.length > 0) && (
            <div className="space-y-2 text-sm">
              {extracted.location && (
                <p className="text-muted-foreground">Location: {extracted.location}</p>
              )}
              {extracted.requirements.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {extracted.requirements.map((r) => (
                    <Badge key={r} variant="outline">{r}</Badge>
                  ))}
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Add application</CardTitle></CardHeader>
        <CardContent>
          <ApplicationForm
            key={seedKey}
            defaultValues={defaultValues}
            aiFilled={aiFilled}
            onSubmit={async (data) => {
              const app = await createApp.mutateAsync(data)
              if (jdText.trim().length > 0) {
                try {
                  await aiApi.putJd(app.id, jdText)
                } catch {
                  // JD store is best-effort; the detail page will prompt "no JD" if missing.
                }
              }
            }}
            onSuccess={() => router.push('/')}
            submitLabel="Add application"
          />
        </CardContent>
      </Card>
    </div>
  )
}
