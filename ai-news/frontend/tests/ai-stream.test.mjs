import assert from 'node:assert/strict'
import test from 'node:test'
import { consumeEventStream, streamChat } from '../src/services/ai.js'

function streamOf(text, size = 3) {
  const bytes = new TextEncoder().encode(text)
  return new ReadableStream({ start(controller) {
    for (let i = 0; i < bytes.length; i += size) controller.enqueue(bytes.slice(i, i + size))
    controller.close()
  } })
}

test('fragmented UTF-8, CRLF and multiline SSE are decoded without losing text', async () => {
  const events = []
  await consumeEventStream(streamOf(': ping\r\n\r\nevent: delta\r\ndata: {"content":\r\ndata: "你好🌍"}\r\n\r\nevent: done\ndata: {}\n\n'), (type, data) => events.push([type, data]))
  assert.deepEqual(events, [['delta', { content: '你好🌍' }], ['done', {}]])
})

test('a terminal frame without a trailing blank line is consumed', async () => {
  const events = []
  await consumeEventStream(streamOf('event: delta\ndata: {"content":"ok"}\n\nevent: done\ndata: {}'), (type, data) => events.push(type))
  assert.deepEqual(events, ['delta', 'done'])
})

test('midstream errors reject while preserving previously delivered text', async () => {
  let text = ''
  await assert.rejects(consumeEventStream(streamOf('event: delta\ndata: {"content":"保留内容"}\n\nevent: error\ndata: {"message":"暂时不可用"}\n\n'), (type, data) => { if (type === 'delta') text += data.content }), /暂时不可用/)
  assert.equal(text, '保留内容')
})

test('an incomplete connection is not silently marked successful', async () => {
  await assert.rejects(consumeEventStream(streamOf('event: delta\ndata: {"content":"partial"}\n\n'), () => {}), /连接意外中断/)
})

test('request validation errors are readable instead of object strings', async (t) => {
  t.mock.method(globalThis, 'fetch', async () => new Response(JSON.stringify({ detail: [{ msg: '对话过长，请开启新对话' }] }), { status: 422, headers: { 'content-type': 'application/json' } }))
  await assert.rejects(streamChat('/api/ai/chat', [{ role: 'user', content: '你好' }], { onDelta() {} }), /对话过长，请开启新对话/)
})
