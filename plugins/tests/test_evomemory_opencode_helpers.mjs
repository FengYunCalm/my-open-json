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
  assert.equal(launch?.env?.MEMPALACE_PALACE_PATH, '/home/tester/.evomemory/palace')
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

test('buildDirectBridgeLaunch prefers existing evomemory palace path over legacy path', () => {
  const launch = buildDirectBridgeLaunch(
    { bridgeBaseUrl: 'http://127.0.0.1:8765' },
    {
      HOME: '/home/tester',
      EVOMEMORY_PALACE_PATH: '/data/evomemory/palace',
      MEMPALACE_PALACE_PATH: '/data/mempalace/palace',
    },
  )

  assert.equal(launch?.env?.EVOMEMORY_PALACE_PATH, '/data/evomemory/palace')
  assert.equal(launch?.env?.MEMPALACE_PALACE_PATH, '/data/evomemory/palace')
})
