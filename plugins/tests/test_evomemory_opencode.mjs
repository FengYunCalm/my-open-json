import test from 'node:test'
import assert from 'node:assert/strict'

import { EvomemoryOpencodePlugin } from '../evomemory-opencode.js'

test('prewarms evomemory bridge during plugin initialization', async () => {
  const originalFetch = globalThis.fetch
  const calls = []

  globalThis.fetch = async (url) => {
    calls.push(String(url))
    return {
      ok: true,
      json: async () => ({ ok: true }),
    }
  }

  try {
    await EvomemoryOpencodePlugin({
      client: {
        app: { log: async () => {} },
        session: { messages: async () => ({ data: [] }) },
      },
      directory: '/home/mechrevo/.config/opencode',
      worktree: '/home/mechrevo/.config/opencode',
    })
  } finally {
    globalThis.fetch = originalFetch
  }

  assert.ok(calls.includes('http://127.0.0.1:8765/health'))
})

test('prefers bridge-provided system_block over local formatting', async () => {
  const originalFetch = globalThis.fetch

  globalThis.fetch = async (url) => {
    if (String(url).endsWith('/health')) {
      return {
        ok: true,
        json: async () => ({ ok: true }),
      }
    }

    if (String(url).endsWith('/internal/context/search')) {
      return {
        ok: true,
        json: async () => ({
          wing: 'opencode',
          system_block: 'bridge supplied block',
          results: [
            {
              drawer_id: 'drawer_should_not_be_rendered_locally',
              search_tier: 'session',
              similarity: 0.99,
              room: 'opencode-session',
              role: 'assistant',
              source_file: 'session:ses_demo',
              text: 'local formatter fallback content',
            },
          ],
        }),
      }
    }

    throw new Error(`unexpected url: ${url}`)
  }

  try {
    const plugin = await EvomemoryOpencodePlugin({
      client: {
        app: { log: async () => {} },
        session: { messages: async () => ({ data: [] }) },
      },
      directory: '/home/mechrevo/.config/opencode',
      worktree: '/home/mechrevo/.config/opencode',
    })

    await plugin['chat.message'](
      { sessionID: 'ses_demo' },
      { parts: [{ type: 'text', text: 'drawer navigation is missing from search results' }] },
    )

    const output = { system: [] }
    await plugin['experimental.chat.system.transform']({ sessionID: 'ses_demo' }, output)

    assert.deepEqual(output.system, ['bridge supplied block'])
  } finally {
    globalThis.fetch = originalFetch
  }
})

test('does not query evomemory for long current-code inspection prompts', async () => {
  const originalFetch = globalThis.fetch
  const calls = []

  globalThis.fetch = async (url) => {
    calls.push(String(url))
    if (String(url).endsWith('/health')) {
      return {
        ok: true,
        json: async () => ({ ok: true }),
      }
    }

    if (String(url).endsWith('/internal/context/search')) {
      throw new Error('should not search evomemory for current-code inspection prompts')
    }

    throw new Error(`unexpected url: ${url}`)
  }

  try {
    const plugin = await EvomemoryOpencodePlugin({
      client: {
        app: { log: async () => {} },
        session: { messages: async () => ({ data: [] }) },
      },
      directory: '/home/mechrevo/.config/opencode',
      worktree: '/home/mechrevo/.config/opencode',
    })

    await plugin['chat.message'](
      { sessionID: 'ses_code_truth' },
      {
        parts: [{ type: 'text', text: 'please explain the current implementation in plugins/tool-forced-eval.js' }],
      },
    )

    const output = { system: [] }
    await plugin['experimental.chat.system.transform']({ sessionID: 'ses_code_truth' }, output)

    assert.deepEqual(output.system, [])
    assert.equal(calls.filter((url) => url.endsWith('/internal/context/search')).length, 0)
  } finally {
    globalThis.fetch = originalFetch
  }
})

test('forwards include_trace and logs retrieval trace when enabled', async () => {
  const originalFetch = globalThis.fetch
  const calls = []
  const logs = []

  globalThis.fetch = async (url, options = {}) => {
    calls.push({ url: String(url), options })
    if (String(url).endsWith('/health')) {
      return {
        ok: true,
        json: async () => ({ ok: true }),
      }
    }

    if (String(url).endsWith('/internal/context/search')) {
      return {
        ok: true,
        json: async () => ({
          wing: 'opencode',
          system_block: 'bridge supplied block',
          results: [],
          retrieval_trace: {
            candidate_count: 3,
            returned_count: 2,
            ranked_candidates: [
              {
                drawer_id: 'drawer_trace_top',
                included: true,
                reasons: ['keyword(git, commit)', 'tier(session)'],
                scores: { total: 0.91 },
              },
            ],
          },
        }),
      }
    }

    throw new Error(`unexpected url: ${url}`)
  }

  try {
    const plugin = await EvomemoryOpencodePlugin({
      client: {
        app: { log: async (entry) => logs.push(entry.body) },
        session: { messages: async () => ({ data: [] }) },
      },
      directory: '/home/mechrevo/.config/opencode',
      worktree: '/home/mechrevo/.config/opencode',
      configOverride: {
        searchIncludeTrace: true,
        logRetrievalTrace: true,
      },
    })

    await plugin['chat.message'](
      { sessionID: 'ses_trace' },
      { parts: [{ type: 'text', text: 'what did we decide earlier about git commit behavior' }] },
    )

    const searchCall = calls.find((entry) => entry.url.endsWith('/internal/context/search'))
    assert.ok(searchCall)
    const body = JSON.parse(searchCall.options.body)
    assert.equal(body.include_trace, true)
    assert.ok(logs.some((entry) => entry.message === 'EvoMemory retrieval trace'))
  } finally {
    globalThis.fetch = originalFetch
  }
})

test('runs maintenance after compaction when enabled', async () => {
  const originalFetch = globalThis.fetch
  const calls = []

  globalThis.fetch = async (url, options = {}) => {
    calls.push({ url: String(url), options })
    if (String(url).endsWith('/health')) {
      return {
        ok: true,
        json: async () => ({ ok: true }),
      }
    }

    if (String(url).endsWith('/internal/session/flush')) {
      return {
        ok: true,
        json: async () => ({ last_saved_message_id: 'msg_compact_1' }),
      }
    }

    if (String(url).endsWith('/internal/maintenance/run')) {
      return {
        ok: true,
        json: async () => ({ profile: 'light', revision: { revised_count: 0 } }),
      }
    }

    throw new Error(`unexpected url: ${url}`)
  }

  try {
    const plugin = await EvomemoryOpencodePlugin({
      client: {
        app: { log: async () => {} },
        session: {
          messages: async () => ({
            data: [
              {
                info: { id: 'msg_compact_1', role: 'user' },
                parts: [{ type: 'text', text: 'remember this compacted context' }],
              },
            ],
          }),
        },
      },
      directory: '/home/mechrevo/.config/opencode',
      worktree: '/home/mechrevo/.config/opencode',
      configOverride: {
        autoRunMaintenanceOnCompact: true,
        maintenanceProfile: 'light',
        maintenanceMinConfidence: 0.7,
        maintenanceLimit: 10,
      },
    })

    const output = { context: [] }
    await plugin['experimental.session.compacting']({ sessionID: 'ses_compact' }, output)

    const maintenanceCall = calls.find((entry) => entry.url.endsWith('/internal/maintenance/run'))
    assert.ok(maintenanceCall)
    const body = JSON.parse(maintenanceCall.options.body)
    assert.equal(body.profile, 'light')
    assert.equal(body.min_confidence, 0.7)
    assert.equal(body.limit, 10)
  } finally {
    globalThis.fetch = originalFetch
  }
})
