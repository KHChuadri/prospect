'use client'

import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import {
  Form, FormField, FormItem, FormLabel, FormControl, FormMessage,
} from '@/components/ui/form'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import type { CreateApplicationInput } from '@/lib/types'

const schema = z.object({
  company:     z.string().min(1, 'Company required').max(200),
  role:        z.string().min(1, 'Role required').max(200),
  source:      z.string().max(100).optional(),
  salaryRange: z.string().optional(),
})
type Schema = z.infer<typeof schema>

interface Props {
  defaultValues?: Partial<Schema>
  onSubmit: (data: CreateApplicationInput) => Promise<void>
  onSuccess: () => void
  submitLabel?: string
  aiFilled?: string[]
}

export function ApplicationForm({ defaultValues, onSubmit, onSuccess, submitLabel = 'Save', aiFilled = [] }: Props) {
  const form = useForm<Schema>({
    resolver: zodResolver(schema),
    defaultValues: { company: '', role: '', source: '', salaryRange: '', ...defaultValues },
  })

  const handleSubmit = async (data: Schema) => {
    await onSubmit(data)
    onSuccess()
  }

  const aiBadge = (name: string) =>
    aiFilled.includes(name) ? (
      <Badge variant="secondary" className="ml-2 text-[10px] uppercase">AI</Badge>
    ) : null

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-4">
        <FormField control={form.control} name="company" render={({ field }) => (
          <FormItem>
            <FormLabel>Company{aiBadge('company')}</FormLabel>
            <FormControl><Input placeholder="Acme Corp" {...field} /></FormControl>
            <FormMessage />
          </FormItem>
        )} />
        <FormField control={form.control} name="role" render={({ field }) => (
          <FormItem>
            <FormLabel>Role{aiBadge('role')}</FormLabel>
            <FormControl><Input placeholder="Software Engineer" {...field} /></FormControl>
            <FormMessage />
          </FormItem>
        )} />
        <FormField control={form.control} name="source" render={({ field }) => (
          <FormItem>
            <FormLabel>
              Source <span className="text-muted-foreground">(optional)</span>
            </FormLabel>
            <FormControl><Input placeholder="LinkedIn, referral…" {...field} /></FormControl>
            <FormMessage />
          </FormItem>
        )} />
        <FormField control={form.control} name="salaryRange" render={({ field }) => (
          <FormItem>
            <FormLabel>
              Salary range <span className="text-muted-foreground">(optional)</span>{aiBadge('salaryRange')}
            </FormLabel>
            <FormControl><Input placeholder="80k–100k" {...field} /></FormControl>
            <FormMessage />
          </FormItem>
        )} />
        {form.formState.errors.root && (
          <p className="text-sm text-destructive">{form.formState.errors.root.message}</p>
        )}
        <Button type="submit" disabled={form.formState.isSubmitting}>
          {form.formState.isSubmitting ? 'Saving…' : submitLabel}
        </Button>
      </form>
    </Form>
  )
}
