import Link from 'next/link'
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table'
import { StatusBadge } from './StatusBadge'
import type { JobApplication } from '@/lib/types'

export function ApplicationTable({ applications }: { applications: JobApplication[] }) {
  if (applications.length === 0) {
    return (
      <p className="py-12 text-center text-muted-foreground">
        No applications yet. Add your first one!
      </p>
    )
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Company</TableHead>
          <TableHead>Role</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Source</TableHead>
          <TableHead>Applied</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {applications.map((app) => (
          <TableRow key={app.id} className="cursor-pointer transition-colors hover:bg-muted/50">
            <TableCell className="font-medium">
              <Link href={`/applications/${app.id}`} className="hover:underline">
                {app.company}
              </Link>
            </TableCell>
            <TableCell>{app.role}</TableCell>
            <TableCell><StatusBadge status={app.status} /></TableCell>
            <TableCell className="text-muted-foreground">{app.source ?? '—'}</TableCell>
            <TableCell className="text-muted-foreground">
              {new Date(app.appliedAt).toLocaleDateString()}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
