import test from 'node:test'
import assert from 'node:assert/strict'

import { ToolForcedEvalPlugin } from '../tool-forced-eval.js'
import { EvomemoryOpencodePlugin } from '../evomemory-opencode.js'

test('tool-forced-eval and evomemory system prompts can coexist', async () => {
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
          system_block: "Optional historical context from EvoMemory for wing 'opencode'. Use only if it directly helps the current request:\n1. [0.99][session] drawer=drawer_demo room=opencode-session role=assistant src=session:ses_demo\n   Prior decision: treat evomemory as a high-value history source.",
          results: [],
        }),
      }
    }

    throw new Error(`unexpected url: ${url}`)
  }

  try {
    const client = {
      app: { log: async () => {} },
      session: { messages: async () => ({ data: [] }) },
    }

    const toolPlugin = await ToolForcedEvalPlugin({
      client,
      directory: '/home/mechrevo/.config/opencode',
      worktree: '/home/mechrevo/.config/opencode',
    })
    const evomemoryPlugin = await EvomemoryOpencodePlugin({
      client,
      directory: '/home/mechrevo/.config/opencode',
      worktree: '/home/mechrevo/.config/opencode',
    })

    const chatOutput = {
      parts: [{ type: 'text', text: 'please review prior project decisions about tool-forced-eval and evomemory guidance' }],
    }

    await toolPlugin['chat.message']({ sessionID: 'ses_demo' }, chatOutput)
    await evomemoryPlugin['chat.message']({ sessionID: 'ses_demo' }, chatOutput)

    const output = { system: [] }
    await toolPlugin['experimental.chat.system.transform']({ sessionID: 'ses_demo', model: {} }, output)
    await evomemoryPlugin['experimental.chat.system.transform']({ sessionID: 'ses_demo', model: {} }, output)

    assert.equal(output.system.length, 2)
    assert.ok(output.system.some((block) => /^<OPENCODE_TOOL_FORCED_EVAL>/.test(block)))
    assert.ok(output.system.some((block) => /Optional historical context from EvoMemory/.test(block)))
  } finally {
    globalThis.fetch = originalFetch
  }
})
