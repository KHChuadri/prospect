import type { Note } from '@/lib/types'
import { Separator } from '@/components/ui/separator'

export function NotesList({ notes }: { notes: Note[] }) {
  if (notes.length === 0) {
    return <p className="text-sm text-muted-foreground">No notes yet.</p>
  }

  return (
    <ul className="space-y-3">
      {notes.map((note, i) => (
        <li key={note.id}>
          <p className="text-sm">{note.content}</p>
          <p className="mt-1 text-xs text-muted-foreground">
            {new Date(note.createdAt).toLocaleString()}
          </p>
          {i < notes.length - 1 && <Separator className="mt-3" />}
        </li>
      ))}
    </ul>
  )
}
