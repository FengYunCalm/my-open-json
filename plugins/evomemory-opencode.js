import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

import {
  buildSystemBlock,
  collectText,
  messagesSinceCheckpoint,
  shouldPersist,
  shouldSearch,
} from "./evomemory-opencode.helpers.mjs";
import { ensureBridge } from "./evomemory-bridge-manager.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const DEFAULTS = {
  bridgeBaseUrl: "http://127.0.0.1:8765",
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
  searchIncludeTrace: false,
  logRetrievalTrace: false,
  maintenanceProfile: "light",
  maintenanceMinConfidence: 0.5,
  maintenanceLimit: 20,
  maintenanceThrottleMs: 300000,
  requestTimeoutMs: 5000,
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
    allowCoreMemory: true,
    lastSavedMessageID: null,
    lastSavedMessageIndex: null,
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

function normalizeSearchPayload(payload) {
  const issues = [];
  const isObject = payload && typeof payload === "object";
  if (!isObject) {
    return {
      issues: ["payload is not an object"],
      value: {
        wing: undefined,
        core_memory: [],
        results: [],
        retrieval_trace: null,
      },
    };
  }

  if (payload.core_memory != null && !Array.isArray(payload.core_memory)) {
    issues.push("invalid core_memory");
  }
  if (payload.results != null && !Array.isArray(payload.results)) {
    issues.push("invalid results");
  }
  if (
    payload.retrieval_trace != null &&
    (typeof payload.retrieval_trace !== "object" ||
      Array.isArray(payload.retrieval_trace))
  ) {
    issues.push("invalid retrieval_trace");
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
      results: Array.isArray(payload.results) ? payload.results : [],
      retrieval_trace:
        payload.retrieval_trace &&
        typeof payload.retrieval_trace === "object" &&
        !Array.isArray(payload.retrieval_trace)
          ? payload.retrieval_trace
          : null,
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
  } finally {
    clearTimeout(timer);
  }
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`${pathname} failed: ${response.status} ${text}`);
  }
  return response.json();
}

function hookMessage(output) {
  if (!output?.message?.id) return null;
  return {
    info: output.message,
    parts: Array.isArray(output.parts) ? output.parts : [],
  };
}

async function getMessages(client, sessionID) {
  const result = await client.session.messages({ path: { id: sessionID } });
  if (result.error) throw new Error(`session.messages failed for ${sessionID}`);
  return result.data ?? [];
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

  await ensureBridge(config, client, dependencies);

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

  function renderBlock(payload) {
    return buildSystemBlock(payload, config.maxInjectedChars, {
      minRetrievalScore: config.minRetrievalScore,
      safeExcerptChars: config.safeExcerptChars,
    });
  }

  async function preloadCoreMemory(sessionID, dir) {
    if (!config.preloadCoreMemory) return null;
    if (!(await ensureBridge(config, client, dependencies))) return null;
    const search = await fetchJson(
      config.bridgeBaseUrl,
      "/internal/context/search",
      {
        method: "POST",
        body: JSON.stringify({
          session_id: sessionID,
          directory: dir,
          query: "stable project memory user preference",
          include_trace: false,
        }),
        requestTimeoutMs: config.requestTimeoutMs,
        fetchImpl: dependencies.fetchImpl,
      },
    );
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
    const coreBlock = renderBlock({
      ...normalizedSearch.value,
      results: [],
    });
    patchSessionState(sessions, sessionID, { coreBlock }, dir);
    await log(client, "debug", "EvoMemory core memory preloaded", {
      sessionID,
      coreMemoryCount: normalizedSearch.value.core_memory.length,
      coreBlockLength: coreBlock.length,
    });
    return coreBlock;
  }

  async function flushSession(sessionID, reason, extraMessages = []) {
    if (!(await ensureBridge(config, client, dependencies))) return null;
    const sessionState = getSessionState(
      sessions,
      sessionID,
      getDirectory(sessionID),
    );
    const messages = await getMessages(client, sessionID);
    const ids = new Set(
      messages.map((message) => message?.info?.id).filter(Boolean),
    );
    const merged = [
      ...messages,
      ...extraMessages.filter((message) => {
        const id = message?.info?.id;
        if (!id || ids.has(id)) return false;
        ids.add(id);
        return true;
      }),
    ];
    const latestMessageID = merged.at(-1)?.info?.id;
    if (latestMessageID && latestMessageID === sessionState.lastSavedMessageID)
      return null;
    const pending = messagesSinceCheckpoint(
      merged,
      sessionState.lastSavedMessageID,
      sessionState.lastSavedMessageIndex,
    );
    if (!pending.length) return null;
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
    const ackIndex = ackID ? findMessageIndex(merged, ackID) : -1;
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
        await flushSession(event.properties.sessionID, "idle").catch((error) =>
          log(client, "warn", "Idle flush failed", {
            sessionID: event.properties.sessionID,
            error: String(error),
          }),
        );
      }
    },

    "chat.message": async ({ sessionID }, output) => {
      const text = collectText(output.parts);
      const allowCoreMemory =
        !shouldPersist(text, config) && !text.trim().startsWith("/");
      patchSessionState(
        sessions,
        sessionID,
        { systemBlock: "", allowCoreMemory },
        getDirectory(sessionID),
      );
      if (config.autoFlushOnMessage && shouldPersist(text, config)) {
        const extra = hookMessage(output);
        await flushSession(sessionID, "message", extra ? [extra] : []).catch(
          (error) =>
            log(client, "warn", "Message flush failed", {
              sessionID,
              error: String(error),
            }),
        );
      }
      if (!shouldSearch(text, config)) return;
      if (!(await ensureBridge(config, client, dependencies))) return;
      const includeTrace = Boolean(
        config.searchIncludeTrace || config.logRetrievalTrace,
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
          requestTimeoutMs: config.requestTimeoutMs,
          fetchImpl: dependencies.fetchImpl,
        },
      ).catch((error) => {
        log(client, "warn", "Context search failed", {
          sessionID,
          error: String(error),
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
      const systemBlock = renderBlock(normalizedSearch.value);
      patchSessionState(
        sessions,
        sessionID,
        { systemBlock },
        getDirectory(sessionID),
      );
      await log(client, "debug", "EvoMemory context search completed", {
        sessionID,
        resultsCount: normalizedSearch.value.results.length,
        coreMemoryCount: normalizedSearch.value.core_memory.length,
        systemBlockLength: systemBlock.length,
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
      const payload = await flushSession(sessionID, "compact").catch(
        (error) => {
          log(client, "warn", "Compaction flush failed", {
            sessionID,
            error: String(error),
          });
          return null;
        },
      );
      if (payload) {
        output.context.push(
          "Recent conversation was persisted to EvoMemory before compaction.",
        );
        await runMaintenance(sessionID).catch((error) => {
          log(client, "warn", "Compaction maintenance failed", {
            sessionID,
            error: String(error),
          });
        });
      }
    },
  };
};
