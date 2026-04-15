import { buildDirectBridgeLaunch } from './mempalace-opencode.helpers.mjs'

const healthCache = new Map()

function getFetchImpl(fetchImpl) {
  return fetchImpl ?? globalThis.fetch
}

function getSpawnImpl(spawnImpl) {
  if (spawnImpl) return spawnImpl
  if (globalThis.Bun?.spawn) return globalThis.Bun.spawn.bind(globalThis.Bun)
  throw new Error('Bun.spawn is unavailable')
}

function getNow(now) {
  return now ?? Date.now
}

async function defaultLog(client, level, message, extra = undefined) {
  await client?.app?.log?.({
    body: { service: 'mempalace-opencode', level, message, extra },
  }).catch(() => {})
}

async function cachedHealthcheck(config, dependencies = {}, options = {}) {
  const fetchImpl = getFetchImpl(dependencies.fetchImpl)
  const now = getNow(dependencies.now)
  const baseUrl = config.bridgeBaseUrl
  const ttlMs = Math.max(0, config.healthcheckCacheTtlMs ?? 1000)
  const force = options.force === true
  const cached = healthCache.get(baseUrl)

  if (!force && ttlMs > 0 && cached && cached.expiresAt > now()) {
    return cached.ok
  }

  let ok = false
  try {
    const response = await fetchImpl(`${baseUrl}/health`)
    if (response.ok) {
      const payload = await response.json()
      ok = payload.ok === true
    }
  } catch {
    ok = false
  }

  if (ttlMs > 0) {
    healthCache.set(baseUrl, { ok, expiresAt: now() + ttlMs })
  } else {
    healthCache.delete(baseUrl)
  }

  return ok
}

export async function bridgeStatus(config, dependencies = {}) {
  return cachedHealthcheck(config, dependencies)
}

export async function waitForBridge(config, dependencies = {}) {
  const sleepImpl = dependencies.sleepImpl ?? ((ms) => new Promise((resolve) => setTimeout(resolve, ms)))
  for (const delay of [250, 500, 1000]) {
    await sleepImpl(delay)
    if (await cachedHealthcheck(config, dependencies, { force: true })) return true
  }
  return false
}

async function startManagedBridge(config, client, dependencies = {}) {
  if (!Array.isArray(config.ensureBridgeCommand) || !config.ensureBridgeCommand.length) return
  const logImpl = dependencies.logImpl ?? defaultLog

  try {
    const spawnImpl = getSpawnImpl(dependencies.spawnImpl)
    const proc = spawnImpl({
      cmd: config.ensureBridgeCommand,
      stdout: 'ignore',
      stderr: 'ignore',
    })
    const exitCode = await proc.exited
    if (exitCode !== 0) {
      await logImpl(client, 'warn', 'ensureBridgeCommand exited non-zero', { exitCode })
    }
  } catch (error) {
    await logImpl(client, 'warn', 'Failed to run ensureBridgeCommand', { error: String(error) })
  }
}

async function startDirectBridge(config, client, dependencies = {}) {
  const launch = buildDirectBridgeLaunch(config)
  if (!launch) return false
  const logImpl = dependencies.logImpl ?? defaultLog

  try {
    const spawnImpl = getSpawnImpl(dependencies.spawnImpl)
    spawnImpl({
      cmd: launch.cmd,
      stdout: 'ignore',
      stderr: 'ignore',
      env: {
        ...process.env,
        ...launch.env,
      },
    })
    await logImpl(client, 'info', 'Started MemPalace bridge via direct fallback')
    return true
  } catch (error) {
    await logImpl(client, 'warn', 'Failed to run direct bridge fallback', { error: String(error) })
    return false
  }
}

export async function ensureBridge(config, client, dependencies = {}) {
  if (await cachedHealthcheck(config, dependencies, { force: true })) return true
  await startManagedBridge(config, client, dependencies)
  if (await waitForBridge(config, dependencies)) return true
  const startedDirectly = await startDirectBridge(config, client, dependencies)
  if (startedDirectly && (await waitForBridge(config, dependencies))) return true
  const logImpl = dependencies.logImpl ?? defaultLog
  await logImpl(client, 'warn', 'MemPalace bridge is unavailable after startup attempt')
  return false
}
