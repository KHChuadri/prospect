// jsdom doesn't implement these web APIs that MSW (via undici) needs.
const { TextEncoder, TextDecoder } = require('util')
const { ReadableStream, WritableStream, TransformStream } = require('stream/web')
const { MessageChannel, MessagePort, BroadcastChannel } = require('worker_threads')

Object.assign(global, {
  TextEncoder,
  TextDecoder,
  ReadableStream,
  WritableStream,
  TransformStream,
  MessageChannel,
  MessagePort,
  BroadcastChannel,
})

const { fetch, Headers, Request, Response, FormData } = require('undici')
Object.assign(global, { fetch, Headers, Request, Response, FormData })
