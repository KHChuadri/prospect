import { cityFromTimezone } from '@/lib/tz'

describe('cityFromTimezone', () => {
  it('takes the city segment', () => {
    expect(cityFromTimezone('Australia/Sydney')).toBe('Sydney')
  })

  it('replaces underscores', () => {
    expect(cityFromTimezone('America/New_York')).toBe('New York')
  })

  it('handles three-segment zones', () => {
    expect(cityFromTimezone('America/Argentina/Buenos_Aires')).toBe('Buenos Aires')
  })

  it('returns null when there is no city segment', () => {
    expect(cityFromTimezone('UTC')).toBeNull()
    expect(cityFromTimezone('')).toBeNull()
  })
})
