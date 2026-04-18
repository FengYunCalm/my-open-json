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

    if (String(url).endsWith('/internal/session/flush')) {
      return {
        ok: true,
        json: async () => ({ last_saved_message_id: 'msg_002' }),
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
              { info: { id: 'msg_001' } },
              { info: { id: 'msg_002' } },
            ],
          }),
        },
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
    assert.ok(calls.findIndex((url) => url.endsWith('/internal/session/flush')) < calls.findIndex((url) => url.endsWith('/internal/context/search')))
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

    if (String(url).endsWith('/internal/session/flush')) {
      return {
        ok: true,
        json: async () => ({ last_saved_message_id: 'msg_code_001' }),
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
            data: [{ info: { id: 'msg_code_001' } }],
          }),
        },
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
    assert.equal(calls.filter((url) => url.endsWith('/internal/session/flush')).length, 1)
  } finally {
    globalThis.fetch = originalFetch
  }
})

test('does not flush evomemory on tiny chinese chatter', async () => {
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

    if (String(url).endsWith('/internal/session/flush') || String(url).endsWith('/internal/context/search')) {
      throw new Error('should not flush or search for tiny chatter')
    }

    throw new Error(`unexpected url: ${url}`)
  }

  try {
    const plugin = await EvomemoryOpencodePlugin({
      client: {
        app: { log: async () => {} },
        session: { messages: async () => ({ data: [{ info: { id: 'msg_chatter_001' } }] }) },
      },
      directory: '/home/mechrevo/.config/opencode',
      worktree: '/home/mechrevo/.config/opencode',
    })

    await plugin['chat.message'](
      { sessionID: 'ses_tiny_zh' },
      {
        parts: [{ type: 'text', text: '好的' }],
      },
    )

    assert.equal(calls.filter((url) => url.endsWith('/internal/session/flush')).length, 0)
    assert.equal(calls.filter((url) => url.endsWith('/internal/context/search')).length, 0)
  } finally {
    globalThis.fetch = originalFetch
  }
})
