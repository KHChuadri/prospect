'use client'

import { useEffect, useRef, useState } from 'react'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Textarea } from '@/components/ui/textarea'
import { Button } from '@/components/ui/button'
import { ResumeProfileCard } from '@/components/resume/ResumeProfileCard'
import { MAX_RESUME_BYTES, useResume, useSaveResume, useUploadResume } from '@/hooks/useAi'
import type { ResumeProfile } from '@/lib/types'

function messageFor(error: unknown, fallback: string) {
  const detail = (error as { response?: { data?: { detail?: string } } })
    ?.response?.data?.detail
  return detail ?? fallback
}

export default function ResumePage() {
  const { data: stored } = useResume()
  const save = useSaveResume()
  const upload = useUploadResume()
  const [text, setText] = useState('')
  const [profile, setProfile] = useState<ResumeProfile | null>(null)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const seeded = useRef(false)

  // Seed the editor once the stored résumé loads.
  useEffect(() => {
    if (stored !== undefined && !seeded.current) {
      setText(stored.text)
      setProfile(stored.profile)
      seeded.current = true
    }
  }, [stored])

  const handleSave = async () => {
    setSaved(false)
    setError(null)
    try {
      await save.mutateAsync(text)
      setSaved(true)
    } catch {
      setError('Could not save — try again.')
    }
  }

  const handleFile = async (file: File | undefined) => {
    if (!file) return
    setSaved(false)
    setError(null)
    setNotice(null)

    // Checked here as well as on the server so an obvious mistake costs the
    // user a round trip rather than an upload.
    if (file.type !== 'application/pdf') {
      setError('Only PDF files are accepted.')
      return
    }
    if (file.size > MAX_RESUME_BYTES) {
      setError('That PDF is larger than 5 MB.')
      return
    }

    try {
      const result = await upload.mutateAsync(file)
      setText(result.text)
      setProfile(result.profile)
      setNotice(result.warning)
    } catch (e) {
      setError(messageFor(e, 'Upload failed — try again.'))
    }
  }

  const busy = upload.isPending

  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <Card>
        <CardHeader><CardTitle>Your résumé</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Upload a PDF and we will pull the text and details out of it, or paste
            it below. Either way it is used to analyse and tailor your applications
            against each job description.
          </p>

          <div className="space-y-1">
            <label htmlFor="resume-pdf" className="text-sm font-medium">
              Upload a PDF
            </label>
            <input
              id="resume-pdf"
              type="file"
              accept="application/pdf"
              disabled={busy}
              onChange={(e) => handleFile(e.target.files?.[0])}
              className="block w-full text-sm file:mr-3 file:rounded file:border-0
                         file:bg-muted file:px-3 file:py-1.5 file:text-sm"
            />
            {busy && (
              <p className="text-sm text-muted-foreground">
                Uploading and reading your résumé…
              </p>
            )}
            {stored?.file_name && !busy && (
              <p className="text-sm text-muted-foreground">
                On file: {stored.file_name}
              </p>
            )}
          </div>

          <Textarea
            value={text}
            onChange={(e) => { setText(e.target.value); setSaved(false); setError(null) }}
            rows={16}
            placeholder="Paste your résumé here…"
          />
          <div className="flex items-center gap-3">
            <Button onClick={handleSave} disabled={save.isPending || busy}>
              {save.isPending ? 'Saving…' : 'Save'}
            </Button>
            {saved && <span className="text-sm text-muted-foreground">Saved.</span>}
            {notice && <span className="text-sm text-muted-foreground">{notice}</span>}
            {error && <span className="text-sm text-destructive">{error}</span>}
          </div>
        </CardContent>
      </Card>

      {profile && <ResumeProfileCard profile={profile} />}
    </div>
  )
}
