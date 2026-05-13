import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

import {
  buildSystemBlock,
  collectText,
  messagesSinceCheckpoint,
  sanitizeHistoricalText,
  shouldPersist,
  shouldSearch,
} from "./evomemory-opencode.helpers.mjs";
import { ensureBridge } from "./evomemory-bridge-manager.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const DEFAULTS = {
  bridgeBaseUrl: "http://127.0.0.1:8765",
  searchMode: "targeted",
  minSearchChars: 16,
  minPersistChars: 8,
  maxInjectedChars: 1800,
  minRetrievalScore: 0.28,
  safeExcerptChars: 180,
  preloadCoreMemory: true,
  autoFlushOnMessage: true,
  autoFlushOnIdle: true,
  autoFlushOnCompact: true,
  autoRunMaintenanceOnCompact: false,
  allowSessionHistoryFlush: false,
  allowLifecycleHistoryFlush: true,
  maxLifecycleHistoryMessages: 40,
  searchIncludeTrace: false,
  logRetrievalTrace: false,
  traceSpineEnabled: false,
  maintenanceProfile: "light",
  maintenanceMinConfidence: 0.5,
  maintenanceLimit: 20,
  maintenanceThrottleMs: 300000,
  requestTimeoutMs: 5000,
  searchRequestTimeoutMs: 1500,
  preloadRequestTimeoutMs: 1000,
  searchFailureCooldownMs: 30000,
  messageFlushWaitMs: 25,
  healthcheckCacheTtlMs: 1000,
  ensureBridgeCommand: [
    "bash",
    "-lc",
    "systemctl --user start evomemory-bridge.service",
  ],
};

function loadConfig() {
  const file = path.join(__dirname, "evomemory-opencode.config.json");
  if (!fs.existsSync(file)) return { ...DEFAULTS };
  try {
    const parsed = JSON.parse(fs.readFileSync(file, "utf8"));
    return { ...DEFAULTS, ...parsed };
  } catch {
    return { ...DEFAULTS };
  }
}

function createSessionState(directory) {
  return {
    directory,
    coreBlock: "",
    systemBlock: "",
    lastTrace: null,
    allowCoreMemory: true,
    lastSavedMessageID: null,
    lastSavedMessageIndex: null,
    flushInFlight: null,
    corePreloadCooldownUntil: 0,
    contextSearchCooldownUntil: 0,
  };
}

function normalizeSessionDirectory(value, fallbackDirectory) {
  return typeof value === "string" && value.trim() ? value : fallbackDirectory;
}

function getSessionState(sessions, sessionID, fallbackDirectory) {
  let state = sessions.get(sessionID);
  if (!state) {
    state = createSessionState(fallbackDirectory);
    sessions.set(sessionID, state);
  }
  return state;
}

function patchSessionState(sessions, sessionID, patch, fallbackDirectory) {
  const current = getSessionState(sessions, sessionID, fallbackDirectory);
  const next = { ...current, ...patch };
  sessions.set(sessionID, next);
  return next;
}

function normalizeFlushPayload(payload) {
  const issues = [];
  const lastSavedMessageID =
    typeof payload?.last_saved_message_id === "string" &&
    payload.last_saved_message_id.trim()
      ? payload.last_saved_message_id
      : null;

  if (
    payload &&
    typeof payload === "object" &&
    payload.last_saved_message_id != null &&
    !lastSavedMessageID
  ) {
    issues.push("invalid last_saved_message_id");
  }

  return { issues, lastSavedMessageID };
}

function normalizeSearchTrace(payload) {
  const normalizedPayload = normalizeSearchPayload(payload).value;
  const rawTrace =
    normalizedPayload.trace && typeof normalizedPayload.trace === "object"
      ? normalizedPayload.trace
      : {};
  const rawRetrievalTrace = normalizedPayload.retrieval_trace ?? {};
  const rankedCandidates = Array.isArray(rawRetrievalTrace.ranked_candidates)
    ? rawRetrievalTrace.ranked_candidates
    : Array.isArray(rawTrace.ranked_candidates)
      ? rawTrace.ranked_candidates
      : [];
  const candidateCount = Number(
    rawTrace.candidate_count ?? rawRetrievalTrace.candidate_count ?? NaN,
  );
  const selectedCount = Number(
    rawTrace.selected_count ??
      rawRetrievalTrace.selected_count ??
      rawRetrievalTrace.returned_count ??
      rankedCandidates.filter((item) => item?.included).length,
  );
  const derivedCandidateCount = Math.max(
    normalizedPayload.results.length,
    normalizedPayload.core_memory.length,
    normalizedPayload.belief_memory.length,
    Array.isArray(normalizedPayload.governance_assets?.genes)
      ? normalizedPayload.governance_assets.genes.length
      : 0,
    Array.isArray(normalizedPayload.governance_assets?.capsules)
      ? normalizedPayload.governance_assets.capsules.length
      : 0,
    rankedCandidates.length,
    Number.isFinite(selectedCount) ? selectedCount : 0,
  );
  return {
    rawTrace,
    rawRetrievalTrace,
    rankedCandidates,
    candidateCount: Number.isFinite(candidateCount)
      ? Math.max(candidateCount, derivedCandidateCount)
      : derivedCandidateCount,
    selectedCount: Number.isFinite(selectedCount) ? selectedCount : 0,
  };
}

function normalizeSearchPayload(payload) {
  const issues = [];
  const isObject = payload && typeof payload === "object";
  if (!isObject) {
    return {
      issues: ["payload is not an object"],
      value: {
        wing: undefined,
        core_memory: [],
        belief_memory: [],
        governance_assets: { genes: [], capsules: [] },
        results: [],
        retrieval_trace: null,
        trace: null,
        system_block: "",
      },
    };
  }

  if (payload.core_memory != null && !Array.isArray(payload.core_memory)) {
    issues.push("invalid core_memory");
  }
  if (payload.belief_memory != null && !Array.isArray(payload.belief_memory)) {
    issues.push("invalid belief_memory");
  }
  if (payload.results != null && !Array.isArray(payload.results)) {
    issues.push("invalid results");
  }
  if (
    payload.governance_assets != null &&
    (typeof payload.governance_assets !== "object" ||
      Array.isArray(payload.governance_assets))
  ) {
    issues.push("invalid governance_assets");
  }
  if (
    payload.retrieval_trace != null &&
    (typeof payload.retrieval_trace !== "object" ||
      Array.isArray(payload.retrieval_trace))
  ) {
    issues.push("invalid retrieval_trace");
  }
  if (
    payload.trace != null &&
    (typeof payload.trace !== "object" || Array.isArray(payload.trace))
  ) {
    issues.push("invalid trace");
  }
  if (
    payload.system_block != null &&
    typeof payload.system_block !== "string"
  ) {
    issues.push("invalid system_block");
  }

  return {
    issues,
    value: {
      wing:
        typeof payload.wing === "string" && payload.wing.trim()
          ? payload.wing
          : undefined,
      core_memory: Array.isArray(payload.core_memory)
        ? payload.core_memory
        : [],
      belief_memory: Array.isArray(payload.belief_memory)
        ? payload.belief_memory
        : [],
      governance_assets:
        payload.governance_assets &&
        typeof payload.governance_assets === "object" &&
        !Array.isArray(payload.governance_assets)
          ? payload.governance_assets
          : { genes: [], capsules: [] },
      results: Array.isArray(payload.results) ? payload.results : [],
      retrieval_trace:
        payload.retrieval_trace &&
        typeof payload.retrieval_trace === "object" &&
        !Array.isArray(payload.retrieval_trace)
          ? payload.retrieval_trace
          : null,
      trace:
        payload.trace && typeof payload.trace === "object" && !Array.isArray(payload.trace)
          ? payload.trace
          : null,
      system_block:
        typeof payload.system_block === "string" ? payload.system_block : "",
    },
  };
}

function findMessageIndex(messages, messageID) {
  return messages.findIndex((message) => message?.info?.id === messageID);
}

async function log(client, level, message, extra = undefined) {
  await client?.app
    ?.log?.({
      body: { service: "evomemory-opencode", level, message, extra },
    })
    .catch(() => {});
}

async function fetchJson(baseUrl, pathname, options = {}) {
  const {
    fetchImpl = globalThis.fetch,
    requestTimeoutMs,
    ...requestOptions
  } = options;
  const timeout = Math.max(1, Number(requestTimeoutMs ?? 5000) || 5000);
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);
  let response;
  try {
    response = await Promise.race([
      fetchImpl(`${baseUrl}${pathname}`, {
        headers: { "Content-Type": "application/json" },
        ...requestOptions,
        signal: controller.signal,
      }),
      new Promise((_, reject) =>
        setTimeout(
          () => reject(new Error(`${pathname} timed out after ${timeout}ms`)),
          timeout,
        ),
      ),
    ]);
    if (!response.ok) {
      const text = await Promise.race([
        response.text(),
        new Promise((_, reject) =>
          setTimeout(
            () => reject(new Error(`${pathname} timed out after ${timeout}ms`)),
            timeout,
          ),
        ),
      ]);
      throw new Error(`${pathname} failed: ${response.status} ${text}`);
    }
    return await Promise.race([
      response.json(),
      new Promise((_, reject) =>
        setTimeout(
          () => reject(new Error(`${pathname} timed out after ${timeout}ms`)),
          timeout,
        ),
      ),
    ]);
  } finally {
    clearTimeout(timer);
  }
}

function hookMessage(output) {
  if (!output?.message?.id) return null;
  return {
    info: output.message,
    parts: Array.isArray(output.parts) ? output.parts : [],
  };
}

function uniqueMessages(messages = []) {
  const seen = new Set();
  return messages.filter((message) => {
    const id = message?.info?.id;
    if (!id || seen.has(id)) return false;
    seen.add(id);
    return true;
  });
}

function limitRecentMessages(messages = [], maxMessages = 0) {
  const limit = Number(maxMessages ?? 0);
  if (!Number.isInteger(limit) || limit <= 0) return [...messages];
  return messages.slice(-limit);
}

async function getMessages(client, sessionID) {
  const result = await client.session.messages({ path: { id: sessionID } });
  if (result.error) throw new Error(`session.messages failed for ${sessionID}`);
  return result.data ?? [];
}

function runDetached(task) {
  const promise = Promise.resolve().then(task);
  promise.catch(() => {});
  return promise;
}

function getClockNow(dependencies) {
  return typeof dependencies.now === "function" ? dependencies.now() : Date.now();
}

function getPositiveDuration(value, fallback) {
  const parsed = Number(value ?? fallback);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

function isTraceEnabled(config) {
  return Boolean(
    config.traceSpineEnabled || config.searchIncludeTrace || config.logRetrievalTrace,
  );
}

function inferTriggerDecision(text, config) {
  const normalized = String(text ?? "").trim();
  return {
    should_persist: shouldPersist(text, config),
    should_search: shouldSearch(text, config),
    prompt_chars: normalized.length,
  };
}

function compactRedactionCounts(redactions = []) {
  const counts = new Map();
  for (const item of redactions) {
    if (!item?.label) continue;
    counts.set(item.label, (counts.get(item.label) ?? 0) + Number(item.count ?? 1));
  }
  return [...counts.entries()].map(([label, count]) => ({ label, count }));
}

function collectRedactionsFromMemory(payload) {
  const redactions = [];
  const inspect = (value) => {
    const before = String(value ?? "");
    const after = sanitizeHistoricalText(before);
    if (before && before !== after) redactions.push({ label: "memory_text", count: 1 });
  };
  for (const item of payload?.core_memory ?? []) {
    inspect(item?.memory_key);
    inspect(item?.memory_value);
  }
  for (const item of payload?.belief_memory ?? []) {
    inspect(item?.key);
    inspect(item?.value);
  }
  for (const item of payload?.governance_assets?.genes ?? []) {
    inspect(item?.key);
    inspect(item?.value);
  }
  for (const item of payload?.results ?? []) {
    inspect(item?.reason_summary);
    inspect(item?.preview ?? item?.text);
  }
  return compactRedactionCounts(redactions);
}

function summarizeChosenCandidates(rankedCandidates = [], results = []) {
  const rankedChosen = rankedCandidates.filter((item) => item?.included);
  const chosen = rankedChosen.length ? rankedChosen : results;
  return chosen.slice(0, 10).map((item) => ({
    id: item?.drawer_id ?? item?.id ?? null,
    reason: sanitizeHistoricalText(
      item?.reason_summary ??
        (Array.isArray(item?.reasons) ? item.reasons.join(", ") : ""),
    ),
  }));
}

function createTraceSpine({
  sessionID,
  directory,
  wing,
  text,
  config,
  searchType,
  requestTimeoutMs,
}) {
  return {
    session_id: sessionID ?? null,
    directory: directory ?? null,
    wing: wing ?? "opencode",
    trigger_decision: inferTriggerDecision(text, config),
    search_type: searchType,
    candidate_count: 0,
    selected_count: 0,
    chosen_results: [],
    injection_budget_used: { characters: 0, estimated_tokens: 0 },
    redactions: [],
    write_capture_decision: "none",
    maintenance_action: "none",
    latency_ms: 0,
    request_timeout_ms: requestTimeoutMs,
    timeout_fallback_reason: null,
    status: "pending",
  };
}

function finalizeTraceSpine(trace, patch = {}) {
  if (!trace) return null;
  return {
    ...trace,
    ...patch,
    redactions: compactRedactionCounts([
      ...(trace.redactions ?? []),
      ...(patch.redactions ?? []),
    ]),
  };
}

function isInCooldown(until, dependencies) {
  return Number(until ?? 0) > getClockNow(dependencies);
}

function markCooldown(
  sessions,
  sessionID,
  field,
  config,
  dependencies,
  fallbackDirectory,
) {
  const cooldownMs = getPositiveDuration(config.searchFailureCooldownMs, 30000);
  patchSessionState(
    sessions,
    sessionID,
    { [field]: getClockNow(dependencies) + cooldownMs },
    fallbackDirectory,
  );
}

async function waitBriefly(promise, timeoutMs) {
  const timeout = Math.max(0, Number(timeoutMs ?? 0) || 0);
  if (timeout === 0) return;
  let timer;
  try {
    await Promise.race([
      promise.catch(() => {}),
      new Promise((resolve) => {
        timer = setTimeout(resolve, timeout);
      }),
    ]);
  } finally {
    clearTimeout(timer);
  }
}

export const EvomemoryOpencodePlugin = async ({
  client,
  directory,
  worktree,
  configOverride,
  fetchImpl,
  spawnImpl,
  sleepImpl,
  now,
  logImpl,
} = {}) => {
  const config = { ...loadConfig(), ...(configOverride ?? {}) };
  const sessions = new Map();
  let lastMaintenanceAt = 0;
  const dependencies = {
    fetchImpl,
    spawnImpl,
    sleepImpl,
    now,
    logImpl,
  };

  const getDirectory = (sessionID) =>
    sessions.get(sessionID)?.directory ?? worktree ?? directory;

  const storeTrace = (sessionID, trace, fallbackDirectory) => {
    if (!isTraceEnabled(config) || !trace) return null;
    patchSessionState(
      sessions,
      sessionID,
      { lastTrace: trace },
      fallbackDirectory ?? getDirectory(sessionID),
    );
    return trace;
  };

  runDetached(() =>
    ensureBridge(config, client, dependencies).catch((error) =>
      log(client, "warn", "EvoMemory bridge prewarm failed", {
        error: String(error),
      }),
    ),
  );

  async function runMaintenance(sessionID) {
    if (!config.autoRunMaintenanceOnCompact) return null;
    const now = Date.now();
    const throttleMs = Math.max(
      0,
      Number(config.maintenanceThrottleMs ?? 0) || 0,
    );
    if (
      throttleMs > 0 &&
      lastMaintenanceAt &&
      now - lastMaintenanceAt < throttleMs
    ) {
      return { skipped: true, reason: "throttled" };
    }
    if (!(await ensureBridge(config, client, dependencies))) return null;
    const payload = await fetchJson(
      config.bridgeBaseUrl,
      "/internal/maintenance/run",
      {
        method: "POST",
        body: JSON.stringify({
          profile: config.maintenanceProfile ?? "light",
          min_confidence: Number(config.maintenanceMinConfidence ?? 0.5),
          limit: Number(config.maintenanceLimit ?? 20),
        }),
        requestTimeoutMs: config.requestTimeoutMs,
        fetchImpl: dependencies.fetchImpl,
      },
    );
    lastMaintenanceAt = now;
    await log(client, "debug", "EvoMemory maintenance completed", {
      sessionID,
      profile: payload?.profile ?? config.maintenanceProfile ?? "light",
      revisedCount: payload?.revision?.revised_count ?? 0,
    });
    return payload;
  }

  function renderBlock(payload, options = {}) {
    return buildSystemBlock(payload, config.maxInjectedChars, {
      currentDirectory: options.currentDirectory,
      minRetrievalScore: config.minRetrievalScore,
      safeExcerptChars: config.safeExcerptChars,
    });
  }

  async function preloadCoreMemory(sessionID, dir) {
    if (!config.preloadCoreMemory) return null;
    if (config.searchMode === "off") return null;
    const session = getSessionState(sessions, sessionID, dir);
    if (isInCooldown(session.corePreloadCooldownUntil, dependencies)) {
      return null;
    }
    if (!(await ensureBridge(config, client, dependencies))) return null;
    let search;
    try {
      search = await fetchJson(config.bridgeBaseUrl, "/internal/context/search", {
        method: "POST",
        body: JSON.stringify({
          session_id: sessionID,
          directory: dir,
          query: "stable project memory user preference",
          include_trace: false,
        }),
        requestTimeoutMs: getPositiveDuration(
          config.preloadRequestTimeoutMs,
          config.requestTimeoutMs,
        ),
        fetchImpl: dependencies.fetchImpl,
      });
    } catch (error) {
      markCooldown(
        sessions,
        sessionID,
        "corePreloadCooldownUntil",
        config,
        dependencies,
        dir,
      );
      throw error;
    }
    const normalizedSearch = normalizeSearchPayload(search);
    if (normalizedSearch.issues.length) {
      await log(
        client,
        "warn",
        "EvoMemory core preload returned unexpected payload",
        {
          sessionID,
          issues: normalizedSearch.issues,
        },
      );
    }
    const coreBlock = renderBlock(
      {
        ...normalizedSearch.value,
        results: [],
      },
      { currentDirectory: dir },
    );
    patchSessionState(sessions, sessionID, { coreBlock }, dir);
    await log(client, "debug", "EvoMemory core memory preloaded", {
      sessionID,
      coreMemoryCount: normalizedSearch.value.core_memory.length,
      coreBlockLength: coreBlock.length,
    });
    return coreBlock;
  }

  async function performFlushSession(sessionID, reason, options = {}) {
    const extraMessages = Array.isArray(options.extraMessages)
      ? options.extraMessages
      : [];
    const loadSessionHistory = options.loadSessionHistory === true;
    const sessionState = getSessionState(
      sessions,
      sessionID,
      getDirectory(sessionID),
    );
    let merged = uniqueMessages(extraMessages);
    if (loadSessionHistory) {
      const messages = limitRecentMessages(
        await getMessages(client, sessionID),
        options.maxSessionHistoryMessages,
      );
      const ids = new Set(
        messages.map((message) => message?.info?.id).filter(Boolean),
      );
      merged = [
        ...messages,
        ...extraMessages.filter((message) => {
          const id = message?.info?.id;
          if (!id || ids.has(id)) return false;
          ids.add(id);
          return true;
        }),
      ];
    }
    const latestMessageID = merged.at(-1)?.info?.id;
    if (latestMessageID && latestMessageID === sessionState.lastSavedMessageID)
      return null;
    const pending = loadSessionHistory
      ? messagesSinceCheckpoint(
          merged,
          sessionState.lastSavedMessageID,
          sessionState.lastSavedMessageIndex,
        )
      : merged;
    if (!pending.length) return null;
    if (!(await ensureBridge(config, client, dependencies))) return null;
    const payload = await fetchJson(
      config.bridgeBaseUrl,
      "/internal/session/flush",
      {
        method: "POST",
        body: JSON.stringify({
          session_id: sessionID,
          directory: sessionState.directory,
          messages: pending,
          reason,
        }),
        requestTimeoutMs: config.requestTimeoutMs,
        fetchImpl: dependencies.fetchImpl,
      },
    );
    const normalized = normalizeFlushPayload(payload);
    if (normalized.issues.length) {
      await log(client, "warn", "EvoMemory flush returned unexpected payload", {
        sessionID,
        issues: normalized.issues,
      });
    }
    const ackID =
      normalized.lastSavedMessageID ??
      sessionState.lastSavedMessageID ??
      latestMessageID ??
      null;
    const ackIndex =
      loadSessionHistory && ackID ? findMessageIndex(merged, ackID) : -1;
    patchSessionState(
      sessions,
      sessionID,
      {
        lastSavedMessageID: ackID,
        lastSavedMessageIndex:
          ackIndex >= 0 ? ackIndex : sessionState.lastSavedMessageIndex,
      },
      getDirectory(sessionID),
    );
    await log(client, "debug", "EvoMemory session flush completed", {
      sessionID,
      reason,
      pendingCount: pending.length,
      ackID,
    });
    return payload;
  }

  async function flushSession(sessionID, reason, options = {}) {
    const fallbackDirectory = getDirectory(sessionID);
    const sessionState = getSessionState(sessions, sessionID, fallbackDirectory);
    const previousFlush = sessionState.flushInFlight ?? Promise.resolve();
    const flush = previousFlush
      .catch(() => {})
      .then(() => performFlushSession(sessionID, reason, options));
    patchSessionState(sessions, sessionID, { flushInFlight: flush }, fallbackDirectory);
    try {
      return await flush;
    } finally {
      const current = getSessionState(sessions, sessionID, getDirectory(sessionID));
      if (current.flushInFlight === flush) {
        patchSessionState(
          sessions,
          sessionID,
          { flushInFlight: null },
          getDirectory(sessionID),
        );
      }
    }
  }

  return {
    event: async ({ event }) => {
      if (event.type === "session.created") {
        const info = event.properties.info;
        patchSessionState(
          sessions,
          info.id,
          { directory: info.directory },
          getDirectory(info.id),
        );
        if (await ensureBridge(config, client, dependencies)) {
          await fetchJson(config.bridgeBaseUrl, "/internal/session/start", {
            method: "POST",
            body: JSON.stringify({
              session_id: info.id,
              directory: info.directory,
            }),
            requestTimeoutMs: config.requestTimeoutMs,
            fetchImpl: dependencies.fetchImpl,
          }).catch(() => {});
          await preloadCoreMemory(info.id, info.directory).catch((error) =>
            log(client, "warn", "Core memory preload failed", {
              sessionID: info.id,
              error: String(error),
            }),
          );
        }
        return;
      }

      if (event.type === "session.updated") {
        const info = event.properties.info;
        const fallbackDirectory = getDirectory(info.id);
        patchSessionState(
          sessions,
          info.id,
          {
            directory: normalizeSessionDirectory(
              info.directory,
              fallbackDirectory,
            ),
          },
          fallbackDirectory,
        );
        return;
      }

      if (event.type === "session.deleted") {
        const info = event.properties.info;
        sessions.delete(info.id);
        return;
      }

      if (event.type === "session.idle" && config.autoFlushOnIdle) {
        await flushSession(event.properties.sessionID, "idle", {
          loadSessionHistory:
            config.allowLifecycleHistoryFlush || config.allowSessionHistoryFlush,
          maxSessionHistoryMessages: config.maxLifecycleHistoryMessages,
        }).catch((error) =>
          log(client, "warn", "Idle flush failed", {
            sessionID: event.properties.sessionID,
            error: String(error),
          }),
        );
      }
    },

    "chat.message": async ({ sessionID }, output) => {
      const text = collectText(output.parts);
      const allowCoreMemory = !text.trim().startsWith("/");
      patchSessionState(
        sessions,
        sessionID,
        { systemBlock: "", lastTrace: null, allowCoreMemory },
        getDirectory(sessionID),
      );
      const traceEnabled = isTraceEnabled(config);
      const traceStart = traceEnabled ? Date.now() : 0;
      const shouldCapture = config.autoFlushOnMessage && shouldPersist(text, config);
      let writeCaptureDecision = shouldCapture ? "message_flush_queued" : "skipped";
      if (shouldCapture) {
        const extra = hookMessage(output);
        const flushPromise = runDetached(() =>
          flushSession(sessionID, "message", {
            extraMessages: extra ? [extra] : [],
            loadSessionHistory: false,
          }).catch((error) =>
            log(client, "warn", "Message flush failed", {
              sessionID,
              error: String(error),
            }),
          ),
        );
        await waitBriefly(flushPromise, config.messageFlushWaitMs);
      }
      const requestTimeoutMs = getPositiveDuration(
        config.searchRequestTimeoutMs,
        config.requestTimeoutMs,
      );
      let trace = traceEnabled
        ? createTraceSpine({
            sessionID,
            directory: getDirectory(sessionID),
            wing: "opencode",
            text,
            config,
            searchType: "context_search",
            requestTimeoutMs,
          })
        : null;
      trace = finalizeTraceSpine(trace, {
        write_capture_decision: writeCaptureDecision,
      });
      if (!shouldSearch(text, config)) {
        const skippedTrace = storeTrace(
          sessionID,
          finalizeTraceSpine(trace, {
            latency_ms: traceEnabled ? Date.now() - traceStart : 0,
            status: "fail-open",
            timeout_fallback_reason: "search_not_triggered",
          }),
        );
        await log(client, "debug", "EvoMemory context search skipped", {
          sessionID,
          trace: traceEnabled ? skippedTrace : undefined,
        });
        return;
      }
      const session = getSessionState(
        sessions,
        sessionID,
        getDirectory(sessionID),
      );
      if (isInCooldown(session.contextSearchCooldownUntil, dependencies)) {
        storeTrace(
          sessionID,
          finalizeTraceSpine(trace, {
            directory: session.directory,
            latency_ms: traceEnabled ? Date.now() - traceStart : 0,
            status: "fail-open",
            timeout_fallback_reason: "search_failure_cooldown",
          }),
          session.directory,
        );
        return;
      }
      if (!(await ensureBridge(config, client, dependencies))) {
        const failedTrace = storeTrace(
          sessionID,
          finalizeTraceSpine(trace, {
            directory: session.directory,
            latency_ms: traceEnabled ? Date.now() - traceStart : 0,
            status: "fail-open",
            timeout_fallback_reason: "bridge_unavailable",
          }),
          session.directory,
        );
        await log(client, "warn", "Context search failed", {
          sessionID,
          error: "bridge unavailable",
          trace: traceEnabled ? failedTrace : undefined,
        });
        return;
      }
      const includeTrace = Boolean(
        config.searchIncludeTrace || config.logRetrievalTrace || config.traceSpineEnabled,
      );
      const search = await fetchJson(
        config.bridgeBaseUrl,
        "/internal/context/search",
        {
          method: "POST",
          body: JSON.stringify({
            session_id: sessionID,
            directory: getDirectory(sessionID),
            query: text,
            include_trace: includeTrace,
          }),
          requestTimeoutMs,
          fetchImpl: dependencies.fetchImpl,
        },
      ).catch((error) => {
        markCooldown(
          sessions,
          sessionID,
          "contextSearchCooldownUntil",
          config,
          dependencies,
          getDirectory(sessionID),
        );
        const failedTrace = storeTrace(
          sessionID,
          finalizeTraceSpine(trace, {
            directory: session.directory,
            latency_ms: traceEnabled ? Date.now() - traceStart : 0,
            status: "fail-open",
            timeout_fallback_reason: String(error).includes("timed out")
              ? "bridge_timeout"
              : "search_failed",
          }),
          session.directory,
        );
        log(client, "warn", "Context search failed", {
          sessionID,
          error: String(error),
          trace: traceEnabled ? failedTrace : undefined,
        });
        return null;
      });
      if (!search) return;
      const normalizedSearch = normalizeSearchPayload(search);
      if (normalizedSearch.issues.length) {
        await log(
          client,
          "warn",
          "EvoMemory search returned unexpected payload",
          {
            sessionID,
            issues: normalizedSearch.issues,
          },
        );
      }
      if (
        config.logRetrievalTrace &&
        normalizedSearch.value.retrieval_trace?.ranked_candidates?.length
      ) {
        const topCandidate =
          normalizedSearch.value.retrieval_trace.ranked_candidates.find(
            (item) => item?.included,
          ) ?? normalizedSearch.value.retrieval_trace.ranked_candidates[0];
        await log(client, "debug", "EvoMemory retrieval trace", {
          sessionID,
          query: text,
          candidateCount:
            normalizedSearch.value.retrieval_trace.candidate_count,
          returnedCount: normalizedSearch.value.retrieval_trace.returned_count,
          topDrawerId: topCandidate?.drawer_id ?? null,
          topReasons: topCandidate?.reasons ?? [],
          topScores: topCandidate?.scores ?? {},
        });
      }
      const systemBlock = renderBlock(normalizedSearch.value, {
        currentDirectory: session.directory,
      });
      const normalizedTrace = normalizeSearchTrace(normalizedSearch.value);
      const backendTrace = normalizedSearch.value.trace ?? {};
      const selectedCount = systemBlock
        ? normalizedTrace.selectedCount || normalizedSearch.value.results.length
        : 0;
      const completedTrace = finalizeTraceSpine(trace, {
        directory: backendTrace.directory ?? session.directory,
        wing: normalizedSearch.value.wing ?? backendTrace.wing ?? trace?.wing,
        candidate_count: normalizedTrace.candidateCount,
        selected_count: selectedCount,
        chosen_results:
          selectedCount > 0
            ? summarizeChosenCandidates(
                normalizedTrace.rankedCandidates,
                normalizedSearch.value.results,
              )
            : [],
        injection_budget_used: {
          characters: systemBlock.length,
          estimated_tokens: Math.ceil(systemBlock.length / 4),
        },
        redactions: collectRedactionsFromMemory(normalizedSearch.value),
        maintenance_action: backendTrace.maintenance_action ?? "none",
        latency_ms: traceEnabled ? Date.now() - traceStart : 0,
        timeout_fallback_reason: backendTrace.timeout_fallback_reason ?? null,
        status: backendTrace.status ?? "ok",
      });
      patchSessionState(
        sessions,
        sessionID,
        { systemBlock, lastTrace: completedTrace },
        getDirectory(sessionID),
      );
      await log(client, "debug", "EvoMemory context search completed", {
        sessionID,
        resultsCount: normalizedSearch.value.results.length,
        coreMemoryCount: normalizedSearch.value.core_memory.length,
        systemBlockLength: systemBlock.length,
        trace: traceEnabled ? completedTrace : undefined,
      });
    },

    "experimental.chat.system.transform": async ({ sessionID }, output) => {
      if (!sessionID) return;
      const session = sessions.get(sessionID);
      if (session?.allowCoreMemory === false && !session?.systemBlock) return;
      const block = session?.systemBlock || session?.coreBlock;
      if (block) {
        output.system.push(block);
        return;
      }
      const loaded = await preloadCoreMemory(
        sessionID,
        getDirectory(sessionID),
      ).catch((error) => {
        log(client, "warn", "Lazy core memory preload failed", {
          sessionID,
          error: String(error),
        });
        return null;
      });
      if (loaded) output.system.push(loaded);
    },

    "experimental.session.compacting": async ({ sessionID }, output) => {
      if (!config.autoFlushOnCompact) return;
      const payload = await flushSession(sessionID, "compact", {
        loadSessionHistory:
          config.allowLifecycleHistoryFlush || config.allowSessionHistoryFlush,
        maxSessionHistoryMessages: config.maxLifecycleHistoryMessages,
      }).catch((error) => {
        log(client, "warn", "Compaction flush failed", {
          sessionID,
          error: String(error),
        });
        return null;
      });
      if (payload) {
        output.context.push(
          "Recent conversation was persisted to EvoMemory before compaction.",
        );
        const maintenancePayload = await runMaintenance(sessionID).catch((error) => ({
          error: String(error),
        }));
        const session = getSessionState(sessions, sessionID, getDirectory(sessionID));
        const maintenanceAction = maintenancePayload?.error
          ? "failed"
          : maintenancePayload?.skipped
            ? `skipped:${maintenancePayload.reason ?? "unknown"}`
            : maintenancePayload
              ? "run"
              : "none";
        const maintenanceTrace =
          isTraceEnabled(config) && session.lastTrace
            ? finalizeTraceSpine(session.lastTrace, {
                maintenance_action: maintenanceAction,
              })
            : null;
        if (maintenanceTrace) {
          storeTrace(sessionID, maintenanceTrace, session.directory);
        }
        if (maintenancePayload?.error) {
          log(client, "warn", "Compaction maintenance failed", {
            sessionID,
            error: maintenancePayload.error,
            trace: maintenanceTrace ?? undefined,
          });
        }
      }
    },
  };
};

export default {
  id: "evomemory-opencode",
  server: EvomemoryOpencodePlugin,
};
