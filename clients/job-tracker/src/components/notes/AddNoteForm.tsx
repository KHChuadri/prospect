'use client'

import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useCreateNote } from '@/hooks/useNotes'
import {
  Form, FormField, FormItem, FormControl, FormMessage,
} from '@/components/ui/form'
import { Textarea } from '@/components/ui/textarea'
import { Button } from '@/components/ui/button'

const schema = z.object({ content: z.string().min(1, 'Content required') })
type Schema = z.infer<typeof schema>

export function AddNoteForm({ applicationId }: { applicationId: number }) {
  const form = useForm<Schema>({
    resolver: zodResolver(schema),
    defaultValues: { content: '' },
  })
  const createNote = useCreateNote(applicationId)

  const onSubmit = async (data: Schema) => {
    await createNote.mutateAsync(data.content)
    form.reset()
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-2">
        <FormField control={form.control} name="content" render={({ field }) => (
          <FormItem>
            <FormControl>
              <Textarea
                placeholder="Write a note…"
                className="min-h-[80px] resize-none"
                {...field}
              />
            </FormControl>
            <FormMessage />
          </FormItem>
        )} />
        <Button type="submit" size="sm" disabled={createNote.isPending}>
          {createNote.isPending ? 'Saving…' : 'Add note'}
        </Button>
      </form>
    </Form>
  )
}
