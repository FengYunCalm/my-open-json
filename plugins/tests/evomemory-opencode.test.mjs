import test from 'node:test'
import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'

import { EvomemoryOpencodePlugin } from '../evomemory-opencode.js'
import * as EvomemoryBridgeManager from '../evomemory-bridge-manager.mjs'
import * as EvomemoryHelpers from '../evomemory-opencode.helpers.mjs'

test('exports evomemory plugin entry', () => {
  assert.equal(typeof EvomemoryOpencodePlugin, 'function')
})

test('ships evomemory plugin config template', () => {
  const path = new URL('../evomemory-opencode.config.json', import.meta.url)
  assert.equal(existsSync(path), true)
  const content = readFileSync(path, 'utf8')
  assert.match(content, /"bridgeBaseUrl"/)
  assert.match(content, /mempalace-bridge\.service/)
})

test('ships richer opencode MCP templates and integration docs', () => {
  const remoteTemplate = new URL('../..//mcp/evomemory/adapters/opencode/opencode.mcp.remote.jsonc', import.meta.url)
  const localTemplate = new URL('../..//mcp/evomemory/adapters/opencode/opencode.mcp.local.jsonc', import.meta.url)
  const readme = new URL('../..//mcp/evomemory/adapters/opencode/README.md', import.meta.url)

  assert.equal(existsSync(remoteTemplate), true)
  assert.equal(existsSync(localTemplate), true)
  assert.equal(existsSync(readme), true)

  const remoteContent = readFileSync(remoteTemplate, 'utf8')
  const localContent = readFileSync(localTemplate, 'utf8')
  const readmeContent = readFileSync(readme, 'utf8')

  assert.match(remoteContent, /"type": "remote"/)
  assert.match(localContent, /"type": "local"/)
  assert.match(readmeContent, /evomemory_search_context/)
  assert.match(readmeContent, /evomemory_record_feedback/)
  assert.match(readmeContent, /opencode\.mcp\.local\.jsonc/)
  assert.match(readmeContent, /opencode\.mcp\.remote\.jsonc/)
})

test('exports evomemory helper and bridge-manager aliases', () => {
  assert.equal(typeof EvomemoryHelpers.collectText, 'function')
  assert.equal(typeof EvomemoryHelpers.shouldSearch, 'function')
  assert.equal(typeof EvomemoryBridgeManager.ensureBridge, 'function')
  assert.equal(typeof EvomemoryBridgeManager.bridgeStatus, 'function')
})
