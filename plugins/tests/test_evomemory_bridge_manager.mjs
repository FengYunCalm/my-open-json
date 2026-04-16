import test from 'node:test'
import assert from 'node:assert/strict'

import {
  bridgeStatus,
  ensureBridge,
} from '../evomemory-bridge-manager.mjs'

test('bridgeStatus caches healthy checks within ttl', async () => {
  let now = 1000
  const calls = []

  const fetchImpl = async (url) => {
    calls.push(String(url))
    return {
      ok: true,
      json: async () => ({ ok: true }),
    }
  }

  const config = {
    bridgeBaseUrl: 'http://127.0.0.1:8765',
    healthcheckCacheTtlMs: 1000,
  }

  assert.equal(await bridgeStatus(config, { fetchImpl, now: () => now }), true)
  assert.equal(await bridgeStatus(config, { fetchImpl, now: () => now }), true)
  assert.equal(calls.length, 1)

  now += 1001
  assert.equal(await bridgeStatus(config, { fetchImpl, now: () => now }), true)
  assert.equal(calls.length, 2)
})

test('ensureBridge falls back to direct launch after managed startup misses health', async () => {
  const spawnCalls = []
  let healthChecks = 0

  const fetchImpl = async (url) => {
    if (!String(url).endsWith('/health')) {
      throw new Error(`unexpected url: ${url}`)
    }
    healthChecks += 1
    const ok = healthChecks >= 5
    return {
      ok,
      json: async () => ({ ok }),
    }
  }

  const spawnImpl = (options) => {
    spawnCalls.push(options.cmd)
    return { exited: Promise.resolve(0) }
  }

  const config = {
    bridgeBaseUrl: 'http://127.0.0.1:8765',
    ensureBridgeCommand: ['bash', '-lc', 'systemctl --user start mempalace-bridge.service'],
    directBridgeCommand: ['python', 'evomemory/interfaces/mcp/server.py', '--host', '127.0.0.1', '--port', '8765'],
    healthcheckCacheTtlMs: 0,
  }

  const ok = await ensureBridge(config, null, {
    fetchImpl,
    spawnImpl,
    sleepImpl: async () => {},
    logImpl: async () => {},
    now: () => Date.now(),
  })

  assert.equal(ok, true)
  assert.deepEqual(spawnCalls, [
    ['bash', '-lc', 'systemctl --user start mempalace-bridge.service'],
    ['python', 'evomemory/interfaces/mcp/server.py', '--host', '127.0.0.1', '--port', '8765'],
  ])
})
