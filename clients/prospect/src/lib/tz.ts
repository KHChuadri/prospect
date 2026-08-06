// Seeds an empty city from the browser's timezone. Deliberately coarse: tz
// identifiers name the largest nearby city, so someone in Newcastle gets
// "Sydney". It only ever prefills — the user can always edit it.
export function cityFromTimezone(tz: string): string | null {
  const segments = tz.split('/')
  if (segments.length < 2) return null
  return segments[segments.length - 1].replace(/_/g, ' ')
}

export function guessCity(): string | null {
  try {
    return cityFromTimezone(Intl.DateTimeFormat().resolvedOptions().timeZone)
  } catch {
    return null
  }
}
