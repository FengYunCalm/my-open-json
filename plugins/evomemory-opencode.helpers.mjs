import path from 'path'
import fs from 'fs'

const SMALL_TALK = new Set(['ok', 'okay', 'yes', 'no', 'thanks', 'thank you', 'continue', 'start', 'go'])

export function collectText(parts = []) {
  return parts
    .filter((part) => part?.type === 'text' && typeof part.text === 'string' && part.text.trim())
    .map((part) => part.text.trim())
    .join('\n\n')
}

export function shouldSearch(text, config = {}) {
  const normalized = (text || '').trim().toLowerCase()
  if (!normalized) return false
  if (normalized.startsWith('/')) return false
  if (normalized.includes('<command-message>')) return false
  if (SMALL_TALK.has(normalized)) return false
  return normalized.length >= (config.minSearchChars ?? 16)
}

export function messagesSinceCheckpoint(messages = [], checkpoint = null) {
  if (!checkpoint) return [...messages]
  const index = messages.findIndex((message) => message?.info?.id === checkpoint)
  if (index === -1) return [...messages]
  return messages.slice(index + 1)
}

export function buildSystemBlock(payload, maxChars = 1800) {
  if (!payload?.results?.length) return ''
  const lines = [
    `EvoMemory context for wing '${payload.wing ?? 'unknown'}':`,
  ]
  let used = lines[0].length
  for (const [index, item] of payload.results.entries()) {
    const tier = item.search_tier ?? 'memory'
    const drawer = item.drawer_id ?? '?'
    const header = `${index + 1}. [${Number(item.similarity ?? 0).toFixed(2)}][${tier}] drawer=${drawer} room=${item.room ?? 'unknown'} role=${item.role ?? 'unknown'} src=${item.source_file ?? '?'}`
    if (used + header.length + 1 > maxChars) break
    lines.push(header)
    used += header.length + 1

    const remaining = maxChars - used - 4
    if (remaining <= 0) break
    const rawText = String(item.text ?? item.preview ?? '')
      .replace(/\s+/g, ' ')
      .trim()
    if (!rawText) continue
    const body = rawText.length > remaining ? `${rawText.slice(0, Math.max(0, remaining - 1))}…` : rawText
    lines.push(`   ${body}`)
    used += body.length + 4
  }
  return lines.join('\n')
}

export function buildDirectBridgeLaunch(config = {}, env = process.env) {
  const home = env.HOME?.trim()
  if (!home) return null

  const bridgeUrl = new URL(config.bridgeBaseUrl ?? 'http://127.0.0.1:8765')
  const sourceRoot = path.join(home, '.config', 'opencode', 'mcp')
  const palacePath =
    env.EVOMEMORY_PALACE_PATH ||
    env.MEMPALACE_PALACE_PATH ||
    path.join(home, '.evomemory', 'palace')
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
      MEMPALACE_PALACE_PATH: palacePath,
      PYTHONPATH: env.PYTHONPATH
        ? [
            ...env.PYTHONPATH.split(path.delimiter).filter(Boolean),
            sourceRoot,
          ].filter((item, index, list) => list.indexOf(item) === index).join(path.delimiter)
        : sourceRoot,
    },
  }
}
