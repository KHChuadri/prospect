'use client'

import { useEffect, useRef, useState } from 'react'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Textarea } from '@/components/ui/textarea'
import { Button } from '@/components/ui/button'
import { useResume, useSaveResume } from '@/hooks/useAi'

export default function ResumePage() {
  const { data: stored } = useResume()
  const save = useSaveResume()
  const [text, setText] = useState('')
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const seeded = useRef(false)

  // Seed the editor once the stored résumé loads.
  useEffect(() => {
    if (stored !== undefined && !seeded.current) {
      setText(stored)
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

  return (
    <div className="mx-auto max-w-2xl">
      <Card>
        <CardHeader><CardTitle>Your résumé</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Paste your résumé as plain text. It is used to analyse and tailor your
            applications against each job description.
          </p>
          <Textarea
            value={text}
            onChange={(e) => { setText(e.target.value); setSaved(false); setError(null) }}
            rows={16}
            placeholder="Paste your résumé here…"
          />
          <div className="flex items-center gap-3">
            <Button onClick={handleSave} disabled={save.isPending}>
              {save.isPending ? 'Saving…' : 'Save'}
            </Button>
            {saved && <span className="text-sm text-muted-foreground">Saved.</span>}
            {error && <span className="text-sm text-destructive">{error}</span>}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
