import test from 'node:test'
import assert from 'node:assert/strict'

import {
  buildDirectBridgeLaunch,
  buildSystemBlock,
  shouldSearch,
} from '../evomemory-opencode.helpers.mjs'

test('shouldSearch ignores tiny small-talk and slash commands', () => {
  assert.equal(shouldSearch('ok', { minSearchChars: 16 }), false)
  assert.equal(shouldSearch('/evomemory:status', { minSearchChars: 16 }), false)
  assert.equal(shouldSearch('drawer navigation is missing from search results', { minSearchChars: 16 }), true)
})

test('shouldSearch prefers history-seeking prompts over current-code inspection prompts', () => {
  assert.equal(
    shouldSearch('please explain the current implementation in plugins/tool-forced-eval.js', { minSearchChars: 16 }),
    false,
  )
  assert.equal(
    shouldSearch('what did we decide earlier about git commit behavior in this project', { minSearchChars: 16 }),
    true,
  )
  assert.equal(
    shouldSearch('remind me of the prior project decisions and stable preferences for evomemory usage', { minSearchChars: 16 }),
    true,
  )
})

test('shouldSearch handles Chinese history prompts and current-code prompts', () => {
  assert.equal(
    shouldSearch('请回顾一下这个项目之前关于自动提交 git commit 的历史决策和用户偏好', { minSearchChars: 16 }),
    true,
  )
  assert.equal(
    shouldSearch('这个模块过去是怎么处理记忆注入的', { minSearchChars: 16 }),
    true,
  )
  assert.equal(
    shouldSearch('请解释一下 plugins/tool-forced-eval.js 这个文件的当前实现', { minSearchChars: 16 }),
    false,
  )
  assert.equal(
    shouldSearch('当前是哪个文件在处理 evomemory 的自动搜索', { minSearchChars: 16 }),
    false,
  )
})

test('buildSystemBlock includes source metadata while staying compact', () => {
  const block = buildSystemBlock(
    {
      wing: 'opencode',
      results: [
        {
          drawer_id: 'drawer_opencode_opencode-session_abc123',
          search_tier: 'session',
          similarity: 0.823,
          room: 'opencode-session',
          role: 'assistant',
          source_file: 'session:ses_demo',
          text: 'Assistant:\nSearch results need drawer ids to become navigable.',
        },
      ],
    },
    240,
  )

  assert.match(block, /Optional historical context from EvoMemory for wing 'opencode'/)
  assert.match(block, /drawer=drawer_opencode_opencode-session_abc123/)
  assert.match(block, /\[session\]/)
  assert.match(block, /room=opencode-session/)
  assert.match(block, /role=assistant/)
  assert.match(block, /src=session:ses_demo/)
  assert.ok(block.length <= 240)
})

test('buildDirectBridgeLaunch derives a direct fallback bridge command', () => {
  const launch = buildDirectBridgeLaunch(
    { bridgeBaseUrl: 'http://127.0.0.1:8765' },
    { HOME: '/home/tester' },
  )

  assert.deepEqual(launch?.cmd, [
    '/home/tester/.local/opt/evomemory-opencode/venv/bin/python',
    '/home/tester/.config/opencode/mcp/evomemory/interfaces/mcp/server.py',
    '--host',
    '127.0.0.1',
    '--port',
    '8765',
  ])
  assert.equal(launch?.env?.EVOMEMORY_PALACE_PATH, '/home/tester/.evomemory/palace')
  assert.deepEqual(Object.keys(launch?.env ?? {}).sort(), ['EVOMEMORY_PALACE_PATH', 'PYTHONPATH'].sort())
  assert.equal(launch?.env?.PYTHONPATH, '/home/tester/.config/opencode/mcp')
})

test('buildDirectBridgeLaunch preserves existing PYTHONPATH while appending evomemory source root', () => {
  const launch = buildDirectBridgeLaunch(
    { bridgeBaseUrl: 'http://127.0.0.1:8765' },
    { HOME: '/home/tester', PYTHONPATH: '/tmp/custom:/opt/lib' },
  )

  assert.equal(
    launch?.env?.PYTHONPATH,
    '/tmp/custom:/opt/lib:/home/tester/.config/opencode/mcp',
  )
})

test('buildDirectBridgeLaunch preserves existing evomemory palace path', () => {
  const launch = buildDirectBridgeLaunch(
    { bridgeBaseUrl: 'http://127.0.0.1:8765' },
    {
      HOME: '/home/tester',
      EVOMEMORY_PALACE_PATH: '/data/evomemory/palace',
    },
  )

  assert.equal(launch?.env?.EVOMEMORY_PALACE_PATH, '/data/evomemory/palace')
  assert.deepEqual(Object.keys(launch?.env ?? {}).sort(), ['EVOMEMORY_PALACE_PATH', 'PYTHONPATH'].sort())
})
