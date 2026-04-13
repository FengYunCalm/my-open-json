import test from 'node:test'
import assert from 'node:assert/strict'

import { buildSystemBlock, shouldSearch } from '../mempalace-opencode.helpers.mjs'

test('shouldSearch ignores tiny small-talk and slash commands', () => {
  assert.equal(shouldSearch('ok', { minSearchChars: 16 }), false)
  assert.equal(shouldSearch('/mempalace:status', { minSearchChars: 16 }), false)
  assert.equal(shouldSearch('drawer navigation is missing from search results', { minSearchChars: 16 }), true)
})

test('buildSystemBlock includes source metadata while staying compact', () => {
  const block = buildSystemBlock(
    {
      wing: 'opencode',
      results: [
        {
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

  assert.match(block, /room=opencode-session/)
  assert.match(block, /role=assistant/)
  assert.match(block, /src=session:ses_demo/)
  assert.ok(block.length <= 240)
})
