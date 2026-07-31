// Imported by jest.setup.ts — starts MSW node server for all tests
import { setupServer } from 'msw/node'
import { handlers } from './handlers'

export const server = setupServer(...handlers)
