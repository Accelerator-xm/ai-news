export async function consumeEventStream(body, onEvent) {
  if (!body) throw new Error('浏览器无法读取流式响应。')
  const reader = body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let completed = false

  const consume = (frame) => {
    const lines = frame.split(/\r?\n/)
    const event = lines.find(line => line.startsWith('event:'))?.slice(6).trim() || 'message'
    const data = lines.filter(line => line.startsWith('data:')).map(line => line.slice(5).replace(/^ /, '')).join('\n')
    if (!data) return
    const payload = JSON.parse(data)
    if (event === 'error') throw new Error(payload.message || '生成中断，请重试。')
    if (event === 'done') completed = true
    onEvent(event, payload)
  }

  try {
    while (true) {
      const { done, value } = await reader.read()
      buffer += done ? decoder.decode() : decoder.decode(value, { stream: true })
      let separator
      while ((separator = /\r?\n\r?\n/.exec(buffer))) {
        consume(buffer.slice(0, separator.index))
        buffer = buffer.slice(separator.index + separator[0].length)
      }
      if (completed) return
      if (done) break
    }
    if (buffer.trim()) consume(buffer)
    if (!completed) throw new Error('连接意外中断，已保留生成内容，请重试。')
  } finally {
    await reader.cancel().catch(() => {})
    reader.releaseLock()
  }
}

export async function streamChat(endpoint, messages, { signal, onDelta }) {
  const response = await fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
    body: JSON.stringify({ messages }),
    signal,
  })
  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    const detail = Array.isArray(error.detail) ? error.detail.map(item => item.msg).join('；') : error.detail
    throw new Error(error.message || detail || `请求失败（${response.status}）`)
  }
  await consumeEventStream(response.body, (event, data) => {
    if (event === 'delta' && typeof data.content === 'string') onDelta(data.content)
  })
}
