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

// jsdom's Blob only implements slice/size/type — no stream(), arrayBuffer() or
// text(). MSW reads a request body by calling stream() on it, so PUTting a File
// (the résumé upload) dies with "object.stream is not a function" before any
// handler runs. Node's implementations carry the full surface.
const { Blob, File } = require('node:buffer')
Object.assign(global, { Blob, File })
