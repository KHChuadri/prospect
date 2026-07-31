import type { Config } from 'jest'
import nextJest from 'next/jest.js'

const createJestConfig = nextJest({ dir: './' })

// MSW v2's subtree publishes ESM (some packages are ESM-only with no CJS build)
// that Jest can't parse as-is. These must be run through Jest's transform.
const MSW_ESM_DEPS = [
  'msw',
  '@mswjs',
  '@open-draft',
  '@bundled-es-modules',
  'until-async',
  'headers-polyfill',
  'rettime',
  'strict-event-emitter',
  'is-node-process',
  'outvariant',
]

const config: Config = {
  setupFiles: ['<rootDir>/jest.polyfills.js'],
  setupFilesAfterEnv: ['<rootDir>/jest.setup.ts'],
  testEnvironment: 'jsdom',
  testMatch: ['**/__tests__/**/*.test.{ts,tsx}'],
  // MSW v2's dual-build deps ship browser/ESM variants jsdom would otherwise
  // resolve; the empty condition opts out so their CJS builds are used.
  testEnvironmentOptions: {
    customExportConditions: [''],
  },
}

// next/jest hard-codes transformIgnorePatterns that block all of node_modules
// except a Next allowlist. `rettime` (a transitive MSW dep) is pure ESM with no
// CJS build, so it MUST be transformed — appending a pattern doesn't help
// because a file is skipped if ANY pattern matches. So we replace them.
const getNextConfig = createJestConfig(config)
export default async () => {
  const nextConfig = await getNextConfig()
  return {
    ...nextConfig,
    transformIgnorePatterns: [
      // MSW v2 and its transitive deps ship ESM that Jest must transform.
      // The .* scan handles pnpm's doubly-nested node_modules layout.
      `/node_modules/(?!.*(${MSW_ESM_DEPS.join('|')}))`,
      // Keep Next's CSS-module exclusion
      '^.+\\.module\\.(css|sass|scss)$',
    ],
  }
}
