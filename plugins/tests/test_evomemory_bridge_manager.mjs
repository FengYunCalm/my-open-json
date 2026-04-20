import test from 'node:test'
import assert from 'node:assert/strict'
import { existsSync, mkdtempSync } from 'node:fs'
import path from 'node:path'
import os from 'node:os'

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
    ensureBridgeCommand: ['bash', '-lc', 'systemctl --user start evomemory-bridge.service'],
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
    ['bash', '-lc', 'systemctl --user start evomemory-bridge.service'],
    ['python', 'evomemory/interfaces/mcp/server.py', '--host', '127.0.0.1', '--port', '8765'],
  ])
})

test('ensureBridge can spawn direct fallback without Bun globals', async () => {
  const tempDir = mkdtempSync(path.join(os.tmpdir(), 'evomemory-bridge-'))
  const markerFile = path.join(tempDir, 'started.txt')

  const originalBun = globalThis.Bun
  try {
    globalThis.Bun = undefined

    const ok = await ensureBridge(
      {
        bridgeBaseUrl: 'http://127.0.0.1:65535',
        ensureBridgeCommand: [],
        directBridgeCommand: [
          process.execPath,
          '-e',
          `require('fs').writeFileSync(${JSON.stringify(markerFile)}, 'ok')`,
        ],
        healthcheckCacheTtlMs: 0,
      },
      null,
      {
        fetchImpl: async () => ({ ok: false, json: async () => ({ ok: false }) }),
        sleepImpl: async () => {},
        logImpl: async () => {},
        now: () => Date.now(),
      },
    )

    await new Promise((resolve) => setTimeout(resolve, 200))
    assert.equal(ok, false)
    assert.equal(existsSync(markerFile), true)
  } finally {
    globalThis.Bun = originalBun
  }
})

test('ensureBridge passes injected env into direct fallback launch', async () => {
  const spawnCalls = []

  const ok = await ensureBridge(
    {
      bridgeBaseUrl: 'http://127.0.0.1:65535',
      ensureBridgeCommand: [],
      healthcheckCacheTtlMs: 0,
    },
    null,
    {
      env: {
        HOME: '/home/tester',
        PYTHONPATH: '/tmp/custom',
        EVOMEMORY_PALACE_PATH: '/data/palace',
      },
      fetchImpl: async () => ({ ok: false, json: async () => ({ ok: false }) }),
      spawnImpl: (options) => {
        spawnCalls.push(options)
        return { exited: Promise.resolve(0) }
      },
      sleepImpl: async () => {},
      logImpl: async () => {},
      now: () => Date.now(),
    },
  )

  assert.equal(ok, false)
  assert.equal(spawnCalls.length, 1)
  assert.deepEqual(spawnCalls[0].cmd, [
    '/home/tester/.local/opt/evomemory-opencode/venv/bin/python',
    '/home/tester/.config/opencode/mcp/evomemory/interfaces/mcp/server.py',
    '--host',
    '127.0.0.1',
    '--port',
    '65535',
  ])
  assert.equal(spawnCalls[0].env.EVOMEMORY_PALACE_PATH, '/data/palace')
  assert.equal(spawnCalls[0].env.PYTHONPATH, '/tmp/custom:/home/tester/.config/opencode/mcp')
})
