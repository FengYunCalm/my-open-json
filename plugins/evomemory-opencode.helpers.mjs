import path from 'path'
import fs from 'fs'

const SMALL_TALK_PATTERNS = [
  /^ok$/i,
  /^okay$/i,
  /^yes$/i,
  /^no$/i,
  /^thanks?$/i,
  /^thank you$/i,
  /^continue$/i,
  /^start$/i,
  /^go$/i,
  /^好$/,
  /^好的$/,
  /^行$/,
  /^收到$/,
  /^继续$/,
  /^开始$/,
  /^谢谢$/,
  /^嗯$/,
  /^嗯嗯$/,
]
const HISTORY_HINTS = [
  /\b(prior|previous|earlier|past|history|historical|remember|remind|decisions?|preferences?|constraint|constraints|feedback|benchmark)\b/i,
  /\bwhat did we decide\b/i,
  /\bused to\b/i,
  /\bstable preferences?\b/i,
  /(之前|先前|以前|过去|历史|历史决策|偏好|约束|反馈|基准|记忆)/,
]
const CURRENT_CODE_HINTS = [
  /\bcurrent implementation\b/i,
  /\bcurrent code\b/i,
  /\bexplain the current implementation\b/i,
  /\bshow me the current\b/i,
  /\b(which|what|this|that|the)\s+(file|function|class)\b/i,
  /\bline \d+\b/i,
  /[\w./-]+\.(js|jsx|ts|tsx|mjs|cjs|py|json|jsonc|md)\b/i,
  /(当前实现|当前代码|第\d+行|这个文件|这个函数|这个类|哪个文件|哪个函数|哪个类)/,
]

export function collectText(parts = []) {
  return parts
    .filter((part) => part?.type === 'text' && typeof part.text === 'string' && part.text.trim())
    .map((part) => part.text.trim())
    .join('\n\n')
}

function normalizeText(text = '') {
  return (text || '').trim().replace(/[!?！？。,.]+$/g, '')
}

export function isLikelySmallTalk(text = '') {
  const normalized = normalizeText(text)
  if (!normalized) return true
  if (normalized.length > 24) return false
  return SMALL_TALK_PATTERNS.some((pattern) => pattern.test(normalized))
}

function shouldIgnore(text = '') {
  const normalized = normalizeText(text)
  if (!normalized) return true
  if (normalized.startsWith('/')) return true
  if (normalized.includes('<command-message>')) return true
  if (isLikelySmallTalk(text)) return true
  return false
}

export function shouldPersist(text, config = {}) {
  if (shouldIgnore(text)) return false
  return normalizeText(text).length >= (config.minPersistChars ?? 8)
}

export function shouldSearch(text, config = {}) {
  const normalized = normalizeText(text)
  if (shouldIgnore(text)) return false
  if (normalized.length < (config.minSearchChars ?? 16)) return false

  const hasHistoryHint = HISTORY_HINTS.some((pattern) => pattern.test(text || ''))
  if (hasHistoryHint) return true

  const hasCurrentCodeHint = CURRENT_CODE_HINTS.some((pattern) => pattern.test(text || ''))
  if (hasCurrentCodeHint) return false

  return true
}

export function messagesSinceCheckpoint(messages = [], checkpoint = null, checkpointIndex = null) {
  if (!checkpoint) return [...messages]
  if (
    Number.isInteger(checkpointIndex)
    && checkpointIndex >= 0
    && checkpointIndex < messages.length
    && messages[checkpointIndex]?.info?.id === checkpoint
  ) {
    return messages.slice(checkpointIndex + 1)
  }
  const index = messages.findIndex((message) => message?.info?.id === checkpoint)
  if (index === -1) return [...messages]
  return messages.slice(index + 1)
}

function normalizeSnippet(text = '') {
  return String(text ?? '')
    .replace(/<[^>]+>/g, ' ')
    .replace(/[`]/g, '')
    .replace(/\b(?:system|developer|assistant|user)\s*:/gi, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

function appendLine(lines, used, next, maxChars) {
  if (typeof next !== 'string') return used
  if (used + next.length + 1 > maxChars) return used
  lines.push(next)
  return used + next.length + 1
}

function buildCoreMemoryLine(item, index) {
  const tier = item.memory_tier ?? 'memory'
  const source = item.source_file ?? '?'
  const key = normalizeSnippet(item.memory_key)
  const value = normalizeSnippet(item.memory_value)
  if (!key || !value) return `${index + 1}. [${tier}] src=${source}`
  return `${index + 1}. [${tier}] ${key}=${value} src=${source}`
}

function buildSearchHitLine(item, index) {
  const tier = item.search_tier ?? 'memory'
  const drawer = item.drawer_id ?? '?'
  const room = item.room ?? 'unknown'
  const role = item.role ?? 'unknown'
  const source = item.source_file ?? '?'
  const reason = normalizeSnippet(item.reason_summary)
  const suffix = reason ? ` why=${reason}` : ''
  return `${index + 1}. [${Number(item.similarity ?? 0).toFixed(2)}][${tier}] drawer=${drawer} room=${room} role=${role} src=${source}${suffix}`
}

export function buildSystemBlock(payload, maxChars = 1800) {
  const coreMemory = Array.isArray(payload?.core_memory) ? payload.core_memory : []
  const results = Array.isArray(payload?.results) ? payload.results : []
  if (!coreMemory.length && !results.length) return ''
  const lines = [
    `Optional historical context from EvoMemory for wing '${payload.wing ?? 'unknown'}'. Use only if it directly helps the current request:`,
  ]
  let used = lines[0].length

  if (coreMemory.length) {
    used = appendLine(lines, used, 'Stable memory:', maxChars)
    for (const [index, item] of coreMemory.entries()) {
      const updated = appendLine(lines, used, buildCoreMemoryLine(item, index), maxChars)
      if (updated === used) break
      used = updated
    }
  }

  if (results.length) {
    if (lines.length > 1) {
      used = appendLine(lines, used, '', maxChars)
    }
    used = appendLine(lines, used, 'Search hits:', maxChars)
    for (const [index, item] of results.entries()) {
      const updated = appendLine(lines, used, buildSearchHitLine(item, index), maxChars)
      if (updated === used) break
      used = updated
    }
  }
  return lines.join('\n')
}

export function buildDirectBridgeLaunch(config = {}, env = process.env) {
  const home = env.HOME?.trim()
  if (!home) return null

  const bridgeUrl = new URL(config.bridgeBaseUrl ?? 'http://127.0.0.1:8765')
  const sourceRoot = path.join(home, '.config', 'opencode', 'mcp')
  const palacePath =
    env.EVOMEMORY_PALACE_PATH || path.join(home, '.evomemory', 'palace')
  const defaultPython = (() => {
    const candidates = [
      path.join(home, '.local', 'opt', 'evomemory-opencode', 'venv', 'bin', 'python'),
      path.join(home, '.config', 'opencode', '.venv', 'bin', 'python'),
    ]
    return candidates.find((file) => fs.existsSync(file)) ?? candidates[0]
  })()
  const directBridgeCommand = Array.isArray(config.directBridgeCommand)
    ? config.directBridgeCommand
    : [
        defaultPython,
        path.join(home, '.config', 'opencode', 'mcp', 'evomemory', 'interfaces', 'mcp', 'server.py'),
        '--host',
        bridgeUrl.hostname,
        '--port',
        bridgeUrl.port || (bridgeUrl.protocol === 'https:' ? '443' : '80'),
      ]

  if (!directBridgeCommand.length) return null

  return {
    cmd: directBridgeCommand,
    env: {
      EVOMEMORY_PALACE_PATH: palacePath,
      PYTHONPATH: env.PYTHONPATH
        ? [
            ...env.PYTHONPATH.split(path.delimiter).filter(Boolean),
            sourceRoot,
          ].filter((item, index, list) => list.indexOf(item) === index).join(path.delimiter)
        : sourceRoot,
    },
  }
}
