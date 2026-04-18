import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

import {
  buildSystemBlock,
  collectText,
  messagesSinceCheckpoint,
  shouldSearch,
} from './evomemory-opencode.helpers.mjs'
import { ensureBridge } from './evomemory-bridge-manager.mjs'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

const DEFAULTS = {
  bridgeBaseUrl: 'http://127.0.0.1:8765',
  minSearchChars: 16,
  maxInjectedChars: 1800,
  autoFlushOnIdle: true,
  autoFlushOnCompact: true,
   autoRunMaintenanceOnCompact: false,
   searchIncludeTrace: false,
   logRetrievalTrace: false,
   maintenanceProfile: 'light',
   maintenanceMinConfidence: 0.5,
   maintenanceLimit: 20,
   maintenanceThrottleMs: 300000,
  healthcheckCacheTtlMs: 1000,
  ensureBridgeCommand: ['bash', '-lc', 'systemctl --user start evomemory-bridge.service'],
}

function loadConfig() {
  const file = path.join(__dirname, 'evomemory-opencode.config.json')
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
    body: { service: 'evomemory-opencode', level, message, extra },
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

async function getMessages(client, sessionID) {
  const result = await client.session.messages({ path: { id: sessionID } })
  if (result.error) throw new Error(`session.messages failed for ${sessionID}`)
  return result.data ?? []
}

export const EvomemoryOpencodePlugin = async ({ client, directory, worktree, configOverride }) => {
  const config = { ...loadConfig(), ...(configOverride ?? {}) }
  const sessions = new Map()
  let lastMaintenanceAt = 0

  const getDirectory = (sessionID) => sessions.get(sessionID)?.directory ?? worktree ?? directory

  await ensureBridge(config, client)

  async function runMaintenance(sessionID) {
    if (!config.autoRunMaintenanceOnCompact) return null
    const now = Date.now()
    const throttleMs = Math.max(0, Number(config.maintenanceThrottleMs ?? 0) || 0)
    if (throttleMs > 0 && lastMaintenanceAt && now - lastMaintenanceAt < throttleMs) {
      return { skipped: true, reason: 'throttled' }
    }
    if (!(await ensureBridge(config, client))) return null
    const payload = await fetchJson(config.bridgeBaseUrl, '/internal/maintenance/run', {
      method: 'POST',
      body: JSON.stringify({
        profile: config.maintenanceProfile ?? 'light',
        min_confidence: Number(config.maintenanceMinConfidence ?? 0.5),
        limit: Number(config.maintenanceLimit ?? 20),
      }),
    })
    lastMaintenanceAt = now
    await log(client, 'debug', 'EvoMemory maintenance completed', {
      sessionID,
      profile: payload?.profile ?? config.maintenanceProfile ?? 'light',
      revisedCount: payload?.revision?.revised_count ?? 0,
    })
    return payload
  }

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
      const includeTrace = Boolean(config.searchIncludeTrace || config.logRetrievalTrace)
      const search = await fetchJson(config.bridgeBaseUrl, '/internal/context/search', {
        method: 'POST',
        body: JSON.stringify({
          session_id: sessionID,
          directory: getDirectory(sessionID),
          query: text,
          include_trace: includeTrace,
        }),
      }).catch((error) => {
        log(client, 'warn', 'Context search failed', { sessionID, error: String(error) })
        return null
      })
      if (!search) return
      if (config.logRetrievalTrace && search.retrieval_trace?.ranked_candidates?.length) {
        const topCandidate = search.retrieval_trace.ranked_candidates.find((item) => item?.included) ?? search.retrieval_trace.ranked_candidates[0]
        await log(client, 'debug', 'EvoMemory retrieval trace', {
          sessionID,
          query: text,
          candidateCount: search.retrieval_trace.candidate_count,
          returnedCount: search.retrieval_trace.returned_count,
          topDrawerId: topCandidate?.drawer_id ?? null,
          topReasons: topCandidate?.reasons ?? [],
          topScores: topCandidate?.scores ?? {},
        })
      }
      sessions.set(sessionID, {
        ...current,
        systemBlock: search.system_block || buildSystemBlock(search, config.maxInjectedChars),
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
        output.context.push('Recent conversation was persisted to EvoMemory before compaction.')
        await runMaintenance(sessionID).catch((error) => {
          log(client, 'warn', 'Compaction maintenance failed', { sessionID, error: String(error) })
        })
      }
    },
  }
}
