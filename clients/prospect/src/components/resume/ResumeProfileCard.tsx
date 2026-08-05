import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import type { ResumeProfile } from '@/lib/types'

export function ResumeProfileCard({ profile }: { profile: ResumeProfile }) {
  const contact = [profile.email, profile.phone, profile.location].filter(Boolean)

  return (
    <Card>
      <CardHeader><CardTitle>Parsed profile</CardTitle></CardHeader>
      <CardContent className="space-y-4 text-sm">
        <div>
          <p className="font-medium">{profile.name || 'Name not found'}</p>
          {contact.length > 0 && (
            <p className="text-muted-foreground">{contact.join(' · ')}</p>
          )}
        </div>

        {profile.skills.length > 0 && (
          <section>
            <h3 className="mb-1 font-medium">Skills</h3>
            <ul className="flex flex-wrap gap-1">
              {profile.skills.map((skill) => (
                <li key={skill} className="rounded bg-muted px-2 py-0.5">{skill}</li>
              ))}
            </ul>
          </section>
        )}

        {profile.experience.length > 0 && (
          <section>
            <h3 className="mb-1 font-medium">Experience</h3>
            <ul className="space-y-2">
              {profile.experience.map((role, i) => (
                <li key={`${role.company}-${i}`}>
                  <p>
                    {role.title} — {role.company}
                    {role.start && (
                      <span className="text-muted-foreground">
                        {' '}({role.start}–{role.end ?? 'present'})
                      </span>
                    )}
                  </p>
                  {role.bullets.length > 0 && (
                    <ul className="ml-4 list-disc text-muted-foreground">
                      {role.bullets.map((bullet, j) => <li key={j}>{bullet}</li>)}
                    </ul>
                  )}
                </li>
              ))}
            </ul>
          </section>
        )}

        {profile.education.length > 0 && (
          <section>
            <h3 className="mb-1 font-medium">Education</h3>
            <ul className="space-y-1">
              {profile.education.map((edu, i) => (
                <li key={`${edu.school}-${i}`}>
                  {edu.degree}, {edu.school}
                  {edu.year && <span className="text-muted-foreground"> ({edu.year})</span>}
                </li>
              ))}
            </ul>
          </section>
        )}
      </CardContent>
    </Card>
  )
}
