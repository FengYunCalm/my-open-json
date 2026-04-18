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
          core_memory: [
            {
              memory_tier: 'project_memory',
              memory_key: 'git_commit_behavior',
              memory_value: 'confirm_first',
              source_file: 'session:ses_demo',
            },
          ],
          results: [
            {
              drawer_id: 'drawer_demo',
              search_tier: 'session',
              similarity: 0.99,
              room: 'opencode-session',
              role: 'assistant',
              source_file: 'session:ses_demo',
              reason_summary: 'keyword(prior, decisions), tier(session)',
            },
          ],
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
