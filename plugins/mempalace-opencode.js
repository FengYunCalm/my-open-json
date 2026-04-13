import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

import {
  buildSystemBlock,
  collectText,
  messagesSinceCheckpoint,
  shouldSearch,
} from './mempalace-opencode.helpers.mjs'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

const DEFAULTS = {
  bridgeBaseUrl: 'http://127.0.0.1:8765',
  minSearchChars: 16,
  maxInjectedChars: 1800,
  autoFlushOnIdle: true,
  autoFlushOnCompact: true,
  ensureBridgeCommand: ['bash', '-lc', 'systemctl --user start mempalace-bridge.service'],
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function loadConfig() {
  const file = path.join(__dirname, 'mempalace-opencode.config.json')
  if (!fs.existsSync(file)) return { ...DEFAULTS }
  try {
    const parsed = JSON.parse(fs.readFileSync(file, 'utf8'))
    return { ...DEFAULTS, ...parsed }
  } catch {
    return { ...DEFAULTS }
  }
}

async function log(client, level, message, extra = undefined) {
  await client?.app?.log?.({
    body: { service: 'mempalace-opencode', level, message, extra },
  }).catch(() => {})
}

async function fetchJson(baseUrl, pathname, options = {}) {
  const response = await fetch(`${baseUrl}${pathname}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!response.ok) {
    const text = await response.text()
    throw new Error(`${pathname} failed: ${response.status} ${text}`)
  }
  return response.json()
}

async function healthcheck(baseUrl) {
  const response = await fetch(`${baseUrl}/health`)
  if (!response.ok) return false
  const payload = await response.json()
  return payload.ok === true
}

async function ensureBridge(config, client) {
  if (await healthcheck(config.bridgeBaseUrl).catch(() => false)) return true
  if (Array.isArray(config.ensureBridgeCommand) && config.ensureBridgeCommand.length) {
    try {
      const proc = Bun.spawn({
        cmd: config.ensureBridgeCommand,
        stdout: 'ignore',
        stderr: 'ignore',
      })
      await proc.exited
    } catch (error) {
      await log(client, 'warn', 'Failed to run ensureBridgeCommand', { error: String(error) })
    }
  }
  for (const delay of [250, 500, 1000]) {
    await sleep(delay)
    if (await healthcheck(config.bridgeBaseUrl).catch(() => false)) return true
  }
  await log(client, 'warn', 'MemPalace bridge is unavailable after startup attempt')
  return false
}

async function getMessages(client, sessionID) {
  const result = await client.session.messages({ path: { id: sessionID } })
  if (result.error) throw new Error(`session.messages failed for ${sessionID}`)
  return result.data ?? []
}

export const MempalaceOpencodePlugin = async ({ client, directory, worktree }) => {
  const config = loadConfig()
  const sessions = new Map()

  const getDirectory = (sessionID) => sessions.get(sessionID)?.directory ?? worktree ?? directory

  async function flushSession(sessionID, reason) {
    if (!(await ensureBridge(config, client))) return null
    const sessionState = sessions.get(sessionID) ?? { directory: getDirectory(sessionID) }
    const messages = await getMessages(client, sessionID)
    const latestMessageID = messages.at(-1)?.info?.id
    const messageSignature = messages.map((message) => message?.info?.id ?? '').join(':')
    if (messageSignature && messageSignature === sessionState.lastSavedSignature) return null
    if (latestMessageID && latestMessageID === sessionState.lastSavedMessageID) return null
    const pending = messagesSinceCheckpoint(messages, sessionState.lastSavedMessageID)
    if (!pending.length) return null
    const payload = await fetchJson(config.bridgeBaseUrl, '/internal/session/flush', {
      method: 'POST',
      body: JSON.stringify({
        session_id: sessionID,
        directory: sessionState.directory,
        messages: pending,
        reason,
      }),
    })
    sessions.set(sessionID, {
      ...sessionState,
      lastSavedMessageID: payload.last_saved_message_id ?? sessionState.lastSavedMessageID,
      lastSavedSignature: messageSignature,
    })
    return payload
  }

  return {
    event: async ({ event }) => {
      if (event.type === 'session.created') {
        const info = event.properties.info
        sessions.set(info.id, { directory: info.directory })
        if (await ensureBridge(config, client)) {
          await fetchJson(config.bridgeBaseUrl, '/internal/session/start', {
            method: 'POST',
            body: JSON.stringify({ session_id: info.id, directory: info.directory }),
          }).catch(() => {})
        }
        return
      }

      if (event.type === 'session.updated') {
        const info = event.properties.info
        const current = sessions.get(info.id) ?? {}
        sessions.set(info.id, {
          ...current,
          directory: info.directory ?? current.directory ?? getDirectory(info.id),
        })
        return
      }

      if (event.type === 'session.deleted') {
        const info = event.properties.info
        sessions.delete(info.id)
        return
      }

      if (event.type === 'session.idle' && config.autoFlushOnIdle) {
        await flushSession(event.properties.sessionID, 'idle').catch((error) =>
          log(client, 'warn', 'Idle flush failed', { sessionID: event.properties.sessionID, error: String(error) }),
        )
      }
    },

    'chat.message': async ({ sessionID }, output) => {
      const text = collectText(output.parts)
      const current = sessions.get(sessionID) ?? { directory: getDirectory(sessionID) }
      sessions.set(sessionID, {
        ...current,
        systemBlock: '',
      })
      if (!shouldSearch(text, config)) return
      if (!(await ensureBridge(config, client))) return
      const search = await fetchJson(config.bridgeBaseUrl, '/internal/context/search', {
        method: 'POST',
        body: JSON.stringify({ session_id: sessionID, directory: getDirectory(sessionID), query: text }),
      }).catch((error) => {
        log(client, 'warn', 'Context search failed', { sessionID, error: String(error) })
        return null
      })
      if (!search) return
      sessions.set(sessionID, {
        ...current,
        systemBlock: buildSystemBlock(search, config.maxInjectedChars),
      })
    },

    'experimental.chat.system.transform': async ({ sessionID }, output) => {
      if (!sessionID) return
      const session = sessions.get(sessionID)
      if (!session?.systemBlock) return
      output.system.push(session.systemBlock)
    },

    'experimental.session.compacting': async ({ sessionID }, output) => {
      if (!config.autoFlushOnCompact) return
      const payload = await flushSession(sessionID, 'compact').catch((error) => {
        log(client, 'warn', 'Compaction flush failed', { sessionID, error: String(error) })
        return null
      })
      if (payload) {
        output.context.push('Recent conversation was persisted to MemPalace before compaction.')
      }
    },
  }
}
