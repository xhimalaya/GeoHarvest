/**
 * Shared client helper for streaming Ollama model pulls via `/api/ai/ollama/pull`.
 */

export const RECOMMENDED_OLLAMA_MODELS: readonly string[] = [
  'qwen2.5-coder:3b',
  'qwen2.5-coder:7b',
  'llama3.2:latest',
  'mistral:latest',
  'gemma3:4b',
]

export interface OllamaPullProgress {
  status: string
  percent: number | null
  completed?: number | null
  total?: number | null
  detailText: string
}

export interface OllamaPullResult {
  model: string
  models: string[]
  ollama?: any
}

export function formatPullProgressText(
  status: string,
  completed?: number | null,
  total?: number | null,
  percent?: number | null
): string {
  if (typeof total === 'number' && total > 0 && typeof completed === 'number') {
    const doneMb = (completed / 1_000_000).toFixed(1)
    const totalMb = (total / 1_000_000).toFixed(1)
    const pct = typeof percent === 'number' ? ` (${percent}%)` : ''
    return `${status}: ${doneMb} / ${totalMb} MB${pct}`
  }
  return status || 'Starting pull...'
}

export async function streamOllamaPull(options: {
  model: string
  baseUrl?: string
  signal?: AbortSignal
  onProgress: (progress: OllamaPullProgress) => void
}): Promise<OllamaPullResult> {
  const targetModel = options.model.trim()
  if (!targetModel) {
    throw new Error('Enter an Ollama model tag to pull (e.g. qwen2.5-coder:3b).')
  }

  const response = await fetch('/api/ai/ollama/pull', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    signal: options.signal,
    body: JSON.stringify({
      model: targetModel,
      base_url: options.baseUrl?.trim() || undefined,
    }),
  })

  if (!response.ok || !response.body) {
    const errJson = await response.json().catch(() => ({}))
    throw new Error(errJson.detail || `Pull request failed (HTTP ${response.status}).`)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let doneResult: OllamaPullResult | null = null

  const processBlock = (block: string) => {
    const lines = block.split(/\r?\n/)
    let evName = 'message'
    const dataLines: string[] = []
    for (const line of lines) {
      if (line.startsWith('event:')) {
        evName = line.slice(6).trim()
      } else if (line.startsWith('data:')) {
        dataLines.push(line.slice(5).trim())
      }
    }
    if (dataLines.length === 0) return

    let payload: any
    try {
      payload = JSON.parse(dataLines.join('\n'))
    } catch {
      return
    }

    if (evName === 'progress') {
      const status = payload.status || 'pulling'
      options.onProgress({
        status,
        percent: typeof payload.percent === 'number' ? payload.percent : null,
        completed: payload.completed ?? null,
        total: payload.total ?? null,
        detailText: formatPullProgressText(status, payload.completed, payload.total, payload.percent),
      })
    } else if (evName === 'error') {
      throw new Error(payload.error || 'Ollama pull failed.')
    } else if (evName === 'done') {
      doneResult = {
        model: payload.model || targetModel,
        models: Array.isArray(payload.models) ? payload.models : [],
        ollama: payload.ollama,
      }
    }
  }

  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const blocks = buffer.split('\n\n')
    buffer = blocks.pop() || ''
    for (const block of blocks) {
      if (block.trim()) processBlock(block)
    }
  }
  if (buffer.trim()) processBlock(buffer)

  return (
    doneResult || {
      model: targetModel,
      models: [targetModel],
    }
  )
}
