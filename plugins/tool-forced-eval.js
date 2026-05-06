/**
 * Route skill and MCP suggestions based on the current task, while keeping the
 * user's objective ahead of workflow nudges.
 */

import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

import {
  buildTaskRouting,
  collectText,
  findGuardedBashCommand,
  getInjectionSkipReason,
} from "./tool-forced-eval.helpers.mjs";
import { createMcpCatalogEntry } from "./tool-forced-eval.mcp.mjs";
import {
  buildSkillLookupRoots,
  loadSkillCatalog,
} from "./tool-forced-eval.skills.mjs";

const MARKER = "<OPENCODE_TOOL_FORCED_EVAL>";
const KNOWN_CONFIG_FILES = ["opencode.json", "opencode.jsonc"];
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PLUGIN_CONFIG_PATH = path.join(__dirname, "tool-forced-eval.config.json");
const STRONG_SKILL_SCORE_THRESHOLD = 4;
const MEDIUM_SKILL_SCORE_THRESHOLD = 2.5;
const SKILL_LEAD_DELTA_THRESHOLD = 1.25;
const REPEATED_SKILL_NUDGE_THRESHOLD = 2;
const STRONG_MCP_SCORE_THRESHOLD = 4;
const REPEATED_MCP_NUDGE_THRESHOLD = 2;
const MAX_CONFIG_CACHE_ENTRIES = 8;

const MERGED_CONFIG_CACHE = new Map();

function getGlobalConfigDir() {
  return path.join(process.env.HOME || "", ".config", "opencode");
}

const DEFAULT_CONFIG = {
  skillReuseTtl: 3,
  shortlistLimit: 3,
  maxReusableSkillsInPrompt: 3,
  emphasizeEvomemory: true,
  includeVisibleMcpAppendixByDefault: false,
  includeVisibleMcpAppendixOnUnclearIntent: true,
  enableBashGuardrails: true,
  bashGuardrailMode: "error",
  guardedBashCommands: ["grep", "find", "cat", "head", "tail"],
};

const TOOL_DESCRIPTION_HINTS = [
  {
    match: (toolID) => toolID === "evomemory_search_context",
    note: "Prefer this early in non-trivial project onboarding, audits, architecture reviews, and cross-file changes when prior decisions, stable constraints, earlier fixes, or historical feedback may matter. Current files remain the source of truth.",
  },
  {
    match: (toolID) => toolID === "evomemory_record_feedback",
    note: "Prefer this when the task confirms or corrects a durable EvoMemory belief, gene, or capsule so memory stays current instead of silently drifting.",
  },
  {
    match: (toolID) =>
      /^evomemory_query_(beliefs|genes|capsules)$/.test(toolID),
    note: "Prefer these when you need to inspect current or stale EvoMemory beliefs, genes, or capsules before deciding whether to record feedback or run maintenance.",
  },
  {
    match: (toolID) => toolID.startsWith("context7_"),
    note: "Prefer this when the task needs current library/framework documentation or official API examples instead of memory-based answers.",
  },
  {
    match: (toolID) => toolID.startsWith("grep_app_"),
    note: "Prefer this when the task needs public GitHub code examples or implementation patterns from open-source repositories.",
  },
  {
    match: (toolID) => toolID.startsWith("fetch_"),
    note: "Prefer this when a concrete URL is already known and the task is to retrieve the page content directly.",
  },
  {
    match: (toolID) => toolID.startsWith("filesystem_"),
    note: "Prefer this when the task needs broader filesystem access or file operations outside the default workspace tools.",
  },
  {
    match: (toolID) => toolID.startsWith("desktop_commander_"),
    note: "Prefer this when the task needs richer local process control, system inspection, or heavyweight local file analysis workflows.",
  },
  {
    match: (toolID) => toolID.startsWith("thinking_"),
    note: "Prefer this when the task benefits from explicit multi-step reasoning, branching analysis, or revising intermediate conclusions.",
  },
  {
    match: (toolID) => toolID.startsWith("memory_"),
    note: "Prefer this when the task needs structured knowledge graph memory, including saved entities, relations, or previously recorded observations.",
  },
  {
    match: (toolID) => toolID.startsWith("evomemory_"),
    note: "Prefer this when the task needs project history, prior decisions, stable preferences, governance constraints, feedback, benchmark results, or historical context for project learning and audits. Automatic plugin injection may have already added some context, but that is not guaranteed. This does not replace reading current code or docs when those are the source of truth.",
  },
];

const BASH_GUARDRAIL_MESSAGES = {
  grep: "Use the dedicated `grep` tool for repository content search instead of shell `grep`.",
  find: "Use `glob` to locate files by path or filename instead of shell `find`.",
  cat: "Use `read` to inspect file contents instead of shell `cat`.",
  head: "Use `read` with `offset` and `limit` instead of shell `head`.",
  tail: "Use `read` with a later `offset` instead of shell `tail`.",
};

const BUILTIN_TOOL_IDS = new Set([
  "apply_patch",
  "bash",
  "codesearch",
  "edit",
  "glob",
  "grep",
  "invalid",
  "list",
  "lsp",
  "multiedit",
  "plan_exit",
  "question",
  "read",
  "skill",
  "task",
  "todowrite",
  "webfetch",
  "websearch",
  "write",
]);

function stripJsonComments(raw) {
  const text = raw.replace(/^\uFEFF/, "");
  let output = "";
  let inString = false;
  let escaped = false;
  let inLineComment = false;
  let inBlockComment = false;

  for (let index = 0; index < text.length; index += 1) {
    const char = text[index];
    const next = text[index + 1];

    if (inLineComment) {
      if (char === "\n" || char === "\r") {
        inLineComment = false;
        output += char;
      }
      continue;
    }

    if (inBlockComment) {
      if (char === "*" && next === "/") {
        inBlockComment = false;
        index += 1;
      }
      continue;
    }

    if (inString) {
      output += char;
      if (escaped) {
        escaped = false;
        continue;
      }
      if (char === "\\") {
        escaped = true;
        continue;
      }
      if (char === '"') {
        inString = false;
      }
      continue;
    }

    if (char === '"') {
      inString = true;
      output += char;
      continue;
    }

    if (char === "/" && next === "/") {
      inLineComment = true;
      index += 1;
      continue;
    }

    if (char === "/" && next === "*") {
      inBlockComment = true;
      index += 1;
      continue;
    }

    output += char;
  }

  return output;
}

function readConfigFile(filePath) {
  if (!fs.existsSync(filePath)) {
    return { data: null, error: null };
  }

  try {
    const raw = fs.readFileSync(filePath, "utf8");
    return {
      data: JSON.parse(stripJsonComments(raw)),
      error: null,
    };
  } catch (error) {
    return {
      data: null,
      error,
    };
  }
}

function readConfigContent(raw) {
  if (typeof raw !== "string" || !raw.trim()) {
    return { data: null, error: null };
  }

  try {
    return {
      data: JSON.parse(stripJsonComments(raw)),
      error: null,
    };
  } catch (error) {
    return {
      data: null,
      error,
    };
  }
}

function normalizeInteger(value, fallback, minimum = 0) {
  if (!Number.isInteger(value) || value < minimum) return fallback;
  return value;
}

function normalizeBoolean(value, fallback) {
  return typeof value === "boolean" ? value : fallback;
}

function normalizeGuardedBashCommands(value, fallback) {
  if (!Array.isArray(value)) return fallback;
  return value
    .map((item) => (typeof item === "string" ? item.trim().toLowerCase() : ""))
    .filter(Boolean);
}

function normalizeConfig(config = {}) {
  return {
    skillReuseTtl: normalizeInteger(
      config.skillReuseTtl,
      DEFAULT_CONFIG.skillReuseTtl,
    ),
    shortlistLimit: normalizeInteger(
      config.shortlistLimit,
      DEFAULT_CONFIG.shortlistLimit,
    ),
    maxReusableSkillsInPrompt: normalizeInteger(
      config.maxReusableSkillsInPrompt,
      DEFAULT_CONFIG.maxReusableSkillsInPrompt,
    ),
    emphasizeEvomemory: normalizeBoolean(
      config.emphasizeEvomemory,
      DEFAULT_CONFIG.emphasizeEvomemory,
    ),
    includeVisibleMcpAppendixByDefault: normalizeBoolean(
      config.includeVisibleMcpAppendixByDefault,
      DEFAULT_CONFIG.includeVisibleMcpAppendixByDefault,
    ),
    includeVisibleMcpAppendixOnUnclearIntent: normalizeBoolean(
      config.includeVisibleMcpAppendixOnUnclearIntent,
      DEFAULT_CONFIG.includeVisibleMcpAppendixOnUnclearIntent,
    ),
    enableBashGuardrails: normalizeBoolean(
      config.enableBashGuardrails,
      DEFAULT_CONFIG.enableBashGuardrails,
    ),
    bashGuardrailMode:
      config.bashGuardrailMode === "error"
        ? "error"
        : DEFAULT_CONFIG.bashGuardrailMode,
    guardedBashCommands: normalizeGuardedBashCommands(
      config.guardedBashCommands,
      DEFAULT_CONFIG.guardedBashCommands,
    ),
  };
}

function loadPluginConfig(overrides = {}, reportIssue = () => {}) {
  const localConfig = readConfigFile(PLUGIN_CONFIG_PATH);
  if (localConfig.error) reportIssue(PLUGIN_CONFIG_PATH, localConfig.error);
  return {
    ...normalizeConfig({
      ...DEFAULT_CONFIG,
      ...(localConfig.data && typeof localConfig.data === "object"
        ? localConfig.data
        : {}),
      ...(overrides && typeof overrides === "object" ? overrides : {}),
    }),
  };
}

function uniqueConfigPaths(directory, worktree) {
  const paths = [];
  const pushKnownConfigs = (dir) => {
    if (!dir) return;
    for (const fileName of KNOWN_CONFIG_FILES) {
      const filePath = path.join(dir, fileName);
      if (fs.existsSync(filePath)) {
        paths.push(filePath);
      }
    }
  };

  pushKnownConfigs(getGlobalConfigDir());

  const customConfigPath = process.env.OPENCODE_CONFIG
    ? path.resolve(process.env.OPENCODE_CONFIG)
    : "";
  if (customConfigPath && fs.existsSync(customConfigPath)) {
    paths.push(customConfigPath);
  }

  for (const dir of [...new Set([worktree, directory].filter(Boolean))]) {
    pushKnownConfigs(dir);
  }

  const customConfigDir = process.env.OPENCODE_CONFIG_DIR
    ? path.resolve(process.env.OPENCODE_CONFIG_DIR)
    : "";
  pushKnownConfigs(customConfigDir);

  return [...new Set(paths.map((filePath) => path.resolve(filePath)))];
}

function fileCacheKey(filePath) {
  try {
    const stat = fs.statSync(filePath, { bigint: true });
    return `${filePath}:${stat.mtimeNs}:${stat.size}`;
  } catch {
    return `${filePath}:missing`;
  }
}

function configCacheKey(directory, worktree, paths) {
  return JSON.stringify({
    directory: directory || "",
    worktree: worktree || "",
    inline: process.env.OPENCODE_CONFIG_CONTENT || "",
    paths: paths.map(fileCacheKey),
  });
}

function isPlainObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function mergeConfigObjects(base, update) {
  const merged = { ...base };

  for (const [key, value] of Object.entries(update)) {
    if (isPlainObject(value) && isPlainObject(merged[key])) {
      merged[key] = mergeConfigObjects(merged[key], value);
      continue;
    }

    merged[key] = value;
  }

  return merged;
}

function loadMergedOpenCodeConfig(
  directory,
  worktree,
  reportIssue = () => {},
  paths = uniqueConfigPaths(directory, worktree),
) {
  let merged = {};

  for (const filePath of paths) {
    const parsed = readConfigFile(filePath);
    if (parsed.error) {
      reportIssue(filePath, parsed.error);
      continue;
    }
    if (!parsed.data || typeof parsed.data !== "object") continue;

    merged = mergeConfigObjects(merged, parsed.data);
  }

  const inlineConfig = readConfigContent(process.env.OPENCODE_CONFIG_CONTENT);
  if (inlineConfig.error) {
    reportIssue("OPENCODE_CONFIG_CONTENT", inlineConfig.error);
  } else if (inlineConfig.data && typeof inlineConfig.data === "object") {
    merged = mergeConfigObjects(merged, inlineConfig.data);
  }

  return merged;
}

function loadCachedMergedOpenCodeConfig(
  directory,
  worktree,
  reportIssue = () => {},
) {
  const paths = uniqueConfigPaths(directory, worktree);
  const key = configCacheKey(directory, worktree, paths);
  const cached = MERGED_CONFIG_CACHE.get(key);
  if (cached) return cached;

  const value = loadMergedOpenCodeConfig(
    directory,
    worktree,
    reportIssue,
    paths,
  );
  if (MERGED_CONFIG_CACHE.size >= MAX_CONFIG_CACHE_ENTRIES)
    MERGED_CONFIG_CACHE.clear();
  MERGED_CONFIG_CACHE.set(key, value);
  return value;
}

function isBuiltinToolID(toolID) {
  return BUILTIN_TOOL_IDS.has(toolID);
}

function resolveAgentName(context = {}, resolvedConfig = {}) {
  const candidate = [
    context.agent,
    context.agentName,
    context.agentID,
    resolvedConfig.default_agent,
    "build",
  ].find((value) => typeof value === "string" && value.trim());

  return candidate ? candidate.trim() : "build";
}

function matchesPattern(pattern, target) {
  const escaped = pattern
    .replace(/[.+^${}()|[\]\\]/g, "\\$&")
    .replace(/\*/g, ".*")
    .replace(/\?/g, ".");
  return new RegExp(`^${escaped}$`).test(target);
}

function resolveRuleDecision(rules, targets = []) {
  if (!isPlainObject(rules)) return undefined;

  let decision;
  for (const [pattern, value] of Object.entries(rules)) {
    if (typeof value !== "string" && typeof value !== "boolean") continue;
    if (targets.some((target) => matchesPattern(pattern, target))) {
      decision = value;
    }
  }

  return decision;
}

function getKnownMcpTargets(name, knownMcpToolIDs = new Map()) {
  return [
    name,
    `${name}_*`,
    `mcp__${name}__*`,
    ...(knownMcpToolIDs.get(name) ? [...knownMcpToolIDs.get(name)] : []),
  ];
}

function getConcreteKnownMcpToolIDs(name, knownMcpToolIDs = new Map()) {
  return knownMcpToolIDs.get(name) ? [...knownMcpToolIDs.get(name)] : [];
}

function getConfiguredMcpTargets(name, rulesList = []) {
  const targets = new Set();
  const prefixes = [`${name}_`, `mcp__${name}__`];

  for (const rules of rulesList) {
    if (!isPlainObject(rules)) continue;
    for (const target of Object.keys(rules)) {
      if (target === name || prefixes.some((prefix) => target.startsWith(prefix))) {
        targets.add(target);
      }
    }
  }

  return [...targets];
}

function areAllKnownTargetsDenied(rules, targets = [], denyValues = new Set()) {
  const concreteTargets = targets.filter(
    (target) => typeof target === "string" && target && !target.includes("*"),
  );
  if (!concreteTargets.length) return false;

  return concreteTargets.every((target) =>
    denyValues.has(resolveRuleDecision(rules, [target])),
  );
}

function rememberKnownMcpToolID(
  toolID,
  resolvedConfig = {},
  knownMcpToolIDs = new Map(),
) {
  if (!toolID || !isPlainObject(resolvedConfig.mcp)) return;

  const matchingNames = Object.keys(resolvedConfig.mcp)
    .filter(
      (name) =>
        toolID === name ||
        toolID.startsWith(`${name}_`) ||
        toolID.startsWith(`mcp__${name}__`),
    )
    .sort(
      (left, right) => right.length - left.length || left.localeCompare(right),
    );

  const matchedName = matchingNames[0];
  if (!matchedName) return;

  const toolIDs = knownMcpToolIDs.get(matchedName) ?? new Set();
  toolIDs.add(toolID);
  knownMcpToolIDs.set(matchedName, toolIDs);
}

function resolveMcpNameFromToolID(
  toolID,
  resolvedConfig = {},
  knownMcpToolIDs = new Map(),
) {
  if (!toolID || !isPlainObject(resolvedConfig.mcp)) return "";

  const names = Object.keys(resolvedConfig.mcp)
    .filter((name) => {
      const knownToolIDs = knownMcpToolIDs.get(name);
      return (
        toolID === name ||
        toolID.startsWith(`${name}_`) ||
        toolID.startsWith(`mcp__${name}__`) ||
        knownToolIDs?.has(toolID)
      );
    })
    .sort(
      (left, right) => right.length - left.length || left.localeCompare(right),
    );

  return names[0] || "";
}

function isMcpAllowed(
  name,
  resolvedConfig = {},
  agentName = "build",
  knownMcpToolIDs = new Map(),
) {
  const agentConfig = isPlainObject(resolvedConfig.agent?.[agentName])
    ? resolvedConfig.agent[agentName]
    : {};
  const targets = [
    ...getKnownMcpTargets(name, knownMcpToolIDs),
    ...getConfiguredMcpTargets(name, [
      resolvedConfig.tools,
      resolvedConfig.permission,
      agentConfig.tools,
      agentConfig.permission,
    ]),
  ];
  const concreteKnownToolIDs = getConcreteKnownMcpToolIDs(
    name,
    knownMcpToolIDs,
  );

  const globalToolDecision = resolveRuleDecision(resolvedConfig.tools, targets);
  const agentToolDecision = resolveRuleDecision(agentConfig.tools, targets);
  if (agentToolDecision === false) {
    return false;
  }
  if (globalToolDecision === false && agentToolDecision !== true) {
    return false;
  }
  if (
    agentToolDecision !== true &&
    areAllKnownTargetsDenied(
      agentConfig.tools,
      concreteKnownToolIDs,
      new Set([false]),
    )
  ) {
    return false;
  }
  if (
    agentToolDecision !== true &&
    areAllKnownTargetsDenied(
      resolvedConfig.tools,
      concreteKnownToolIDs,
      new Set([false]),
    )
  ) {
    return false;
  }

  const globalPermissionDecision = resolveRuleDecision(
    resolvedConfig.permission,
    targets,
  );
  const agentPermissionDecision = resolveRuleDecision(
    agentConfig.permission,
    targets,
  );
  if (agentPermissionDecision === "deny") return false;
  if (
    globalPermissionDecision === "deny" &&
    agentPermissionDecision !== "allow" &&
    agentPermissionDecision !== "ask"
  )
    return false;
  if (
    agentPermissionDecision !== "allow" &&
    agentPermissionDecision !== "ask" &&
    areAllKnownTargetsDenied(
      agentConfig.permission,
      concreteKnownToolIDs,
      new Set(["deny"]),
    )
  ) {
    return false;
  }
  if (
    agentPermissionDecision !== "allow" &&
    agentPermissionDecision !== "ask" &&
    areAllKnownTargetsDenied(
      resolvedConfig.permission,
      concreteKnownToolIDs,
      new Set(["deny"]),
    )
  ) {
    return false;
  }

  return true;
}

function isSkillToolAllowed(resolvedConfig = {}, agentName = "build") {
  const agentConfig = isPlainObject(resolvedConfig.agent?.[agentName])
    ? resolvedConfig.agent[agentName]
    : {};
  if (agentConfig.tools?.skill === false) return false;
  if (
    resolvedConfig.tools?.skill === false &&
    agentConfig.tools?.skill !== true
  )
    return false;

  if (typeof agentConfig.permission?.skill === "string") {
    if (agentConfig.permission.skill === "deny") return false;
  }
  if (
    typeof resolvedConfig.permission?.skill === "string" &&
    resolvedConfig.permission.skill === "deny" &&
    agentConfig.permission?.skill !== "allow" &&
    agentConfig.permission?.skill !== "ask"
  ) {
    return false;
  }

  return true;
}

function isSkillAllowed(name, resolvedConfig = {}, agentName = "build") {
  if (!isSkillToolAllowed(resolvedConfig, agentName)) return false;

  const agentConfig = isPlainObject(resolvedConfig.agent?.[agentName])
    ? resolvedConfig.agent[agentName]
    : {};
  const agentDecision = resolveRuleDecision(agentConfig.permission?.skill, [
    name,
  ]);
  if (agentDecision === "deny") return false;
  if (agentDecision === "allow" || agentDecision === "ask") return true;

  const globalDecision = resolveRuleDecision(resolvedConfig.permission?.skill, [
    name,
  ]);
  if (globalDecision === "deny") return false;

  return true;
}

function loadVisibleMcpCatalog(
  resolvedConfig = {},
  agentName = "build",
  knownMcpToolIDs = new Map(),
) {
  const merged = resolvedConfig.mcp;
  if (!merged || typeof merged !== "object") return [];

  return Object.entries(merged)
    .filter(
      ([, entryConfig]) =>
        entryConfig &&
        typeof entryConfig === "object" &&
        entryConfig.enabled !== false,
    )
    .filter(([name]) =>
      isMcpAllowed(name, resolvedConfig, agentName, knownMcpToolIDs),
    )
    .map(([name, entryConfig]) => createMcpCatalogEntry(name, entryConfig))
    .sort((left, right) => left.name.localeCompare(right.name));
}

function buildMcpSummaryLines(mcpCatalog) {
  if (!mcpCatalog.length) {
    return [
      "- No enabled MCP tools were discovered from the visible local config files. Continue with native tools unless a stronger external capability is actually needed.",
    ];
  }

  return mcpCatalog.map(
    (entry) =>
      `- \`${entry.name}\`: ${entry.summary || "specialized external tool capability"}.`,
  );
}

function createSessionState() {
  return {
    turn: 0,
    generation: 0,
    loadedSkills: new Map(),
    loadedMcps: new Map(),
    instruction: null,
    skillNudge: null,
    mcpNudge: null,
  };
}

function getSessionState(sessionStates, sessionID) {
  let state = sessionStates.get(sessionID);
  if (!state) {
    state = createSessionState();
    sessionStates.set(sessionID, state);
  }

  return state;
}

function clearInstruction(state) {
  state.instruction = null;
}

function resetForCompaction(state) {
  state.generation += 1;
  clearInstruction(state);
  state.skillNudge = null;
  state.mcpNudge = null;
}

function setInstructionForTurn(state, instruction) {
  state.instruction = instruction;
}

function recordSkillLoad(state, skillName) {
  state.loadedSkills.set(skillName, {
    loadedAtTurn: state.turn,
    generation: state.generation,
  });
  if (state.skillNudge?.name === skillName) {
    state.skillNudge = null;
  }
}

function recordMcpUse(state, mcpName) {
  state.loadedMcps.set(mcpName, {
    loadedAtTurn: state.turn,
    generation: state.generation,
  });
  if (state.mcpNudge?.name === mcpName) {
    state.mcpNudge = null;
  }
}

function getBashCommand(input, output) {
  return String(input?.args?.command ?? output?.args?.command ?? "");
}

function getReusableSkills(state, config) {
  const reusable = [];

  for (const [name, record] of Array.from(state.loadedSkills.entries())) {
    const sameGeneration = record.generation === state.generation;
    const withinTtl = state.turn - record.loadedAtTurn <= config.skillReuseTtl;

    if (!sameGeneration || !withinTtl) {
      state.loadedSkills.delete(name);
      continue;
    }

    reusable.push({
      name,
      loadedAtTurn: record.loadedAtTurn,
    });
  }

  return reusable
    .sort(
      (left, right) =>
        right.loadedAtTurn - left.loadedAtTurn ||
        left.name.localeCompare(right.name),
    )
    .slice(0, config.maxReusableSkillsInPrompt)
    .map((entry) => entry.name);
}

function getReusableMcps(state, config) {
  const reusable = [];

  for (const [name, record] of Array.from(state.loadedMcps.entries())) {
    const sameGeneration = record.generation === state.generation;
    const withinTtl = state.turn - record.loadedAtTurn <= config.skillReuseTtl;

    if (!sameGeneration || !withinTtl) {
      state.loadedMcps.delete(name);
      continue;
    }

    reusable.push({
      name,
      loadedAtTurn: record.loadedAtTurn,
    });
  }

  return reusable
    .sort(
      (left, right) =>
        right.loadedAtTurn - left.loadedAtTurn ||
        left.name.localeCompare(right.name),
    )
    .slice(0, config.maxReusableSkillsInPrompt)
    .map((entry) => entry.name);
}

function isRecentlyUsed(map, state, config, name) {
  if (!name) return false;
  const record = map.get(name);
  if (!record || record.generation !== state.generation) return false;
  return state.turn - record.loadedAtTurn <= config.skillReuseTtl;
}

function buildReusableSkillLines(reusableSkills) {
  if (!reusableSkills.length) return [];

  return [
    "Reusable skills from this session:",
    ...reusableSkills.map((name) => `- \`${name}\``),
    "",
  ];
}

function buildReusableMcpLines(reusableMcps) {
  if (!reusableMcps.length) return [];

  return [
    "Reusable MCP tools from this session:",
    ...reusableMcps.map((name) => `- \`${name}_*\``),
    "",
  ];
}

function buildToolMappingLines() {
  return [
    "Tool mapping:",
    "- `TodoWrite` -> `todowrite`, `Task` -> `task`, `Skill` -> `skill`, file read/write/edit/bash -> native workspace tools.",
    "",
  ];
}

function updateMcpNudgeState(state, mcps, config) {
  const topMcp = mcps[0];
  if (!topMcp) {
    state.mcpNudge = null;
    return null;
  }

  if (isRecentlyUsed(state.loadedMcps, state, config, topMcp.name)) {
    state.mcpNudge = null;
    return {
      mode: "recent",
      topMcp,
      repeatedCount: 1,
    };
  }

  if (
    (topMcp.score ?? 0) < STRONG_MCP_SCORE_THRESHOLD &&
    !topMcp.triggerMatched
  ) {
    state.mcpNudge = null;
    return {
      mode: "soft",
      topMcp,
      repeatedCount: 1,
    };
  }

  const previous = state.mcpNudge;
  const repeatedCount =
    previous &&
    previous.generation === state.generation &&
    previous.name === topMcp.name
      ? previous.repeatedCount + 1
      : 1;

  state.mcpNudge = {
    name: topMcp.name,
    repeatedCount,
    generation: state.generation,
    score: topMcp.score ?? 0,
    turn: state.turn,
  };

  return {
    mode: repeatedCount >= REPEATED_MCP_NUDGE_THRESHOLD ? "escalate" : "strong",
    topMcp,
    repeatedCount,
  };
}

function updateSkillNudgeState(state, skills, config) {
  const topSkill = skills[0];
  if (!topSkill) {
    state.skillNudge = null;
    return null;
  }

  if (isRecentlyUsed(state.loadedSkills, state, config, topSkill.name)) {
    state.skillNudge = null;
    return {
      mode: "recent",
      topSkill,
      repeatedCount: 1,
    };
  }

  const secondSkill = skills[1];
  const scoreLead = (topSkill.score ?? 0) - (secondSkill?.score ?? 0);
  const hasStrongSignal =
    (topSkill.score ?? 0) >= STRONG_SKILL_SCORE_THRESHOLD ||
    topSkill.triggerMatched;
  const hasMediumSignal =
    !hasStrongSignal &&
    (topSkill.score ?? 0) >= MEDIUM_SKILL_SCORE_THRESHOLD &&
    scoreLead >= SKILL_LEAD_DELTA_THRESHOLD;

  if (!hasStrongSignal && !hasMediumSignal) {
    state.skillNudge = null;
    return {
      mode: "soft",
      topSkill,
      repeatedCount: 1,
    };
  }

  const previous = state.skillNudge;
  const repeatedCount =
    previous &&
    previous.generation === state.generation &&
    previous.name === topSkill.name
      ? previous.repeatedCount + 1
      : 1;

  state.skillNudge = {
    name: topSkill.name,
    repeatedCount,
    generation: state.generation,
    score: topSkill.score ?? 0,
    mode: hasStrongSignal ? "strong" : "medium",
    turn: state.turn,
  };

  return {
    mode:
      repeatedCount >= REPEATED_SKILL_NUDGE_THRESHOLD
        ? "escalate"
        : hasStrongSignal
          ? "strong"
          : "medium",
    topSkill,
    repeatedCount,
  };
}

function buildSkillLines(skills, skillNudge) {
  if (!skills.length) return [];

  if (skillNudge?.mode === "recent") {
    return [];
  }

  if (
    skillNudge?.mode === "strong" ||
    skillNudge?.mode === "medium" ||
    skillNudge?.mode === "escalate"
  ) {
    return [
      "### Skill Gate",
      skillNudge.mode === "escalate"
        ? `- The same likely best-fit skill keeps matching this task. Load \`${skillNudge.topSkill.name}\` now unless you have a concrete reason not to.`
        : skillNudge.mode === "strong"
          ? `- A high-confidence skill match exists. Before custom exploration or implementation, decide whether to load \`${skillNudge.topSkill.name}\`.`
          : `- A likely best-fit skill exists. Before manual exploration or implementation, decide whether to load \`${skillNudge.topSkill.name}\`.`,
      "- Default for non-trivial tasks: load the best-matching skill first. Skip only if the task is trivial or none of the suggested skills truly fits.",
      "Suggested skills for this task:",
      ...skills.map(
        (skill) =>
          `- \`${skill.name}\`: ${skill.reason || "Use this when it directly helps the task."}`,
      ),
      "",
    ];
  }

  return [
    "Suggested skills for this task:",
    "- Check these before recreating the workflow manually.",
    ...skills.map(
      (skill) =>
        `- \`${skill.name}\`: ${skill.reason || "Use this when it directly helps the task."}`,
    ),
    "",
  ];
}

function buildNativeToolLines(nativeTools) {
  if (!nativeTools.length) return [];

  return [
    "Preferred native tools right now:",
    ...nativeTools.map((tool) => `- \`${tool.name}\`: ${tool.reason}`),
    "",
  ];
}

function shouldSuppressSkillSuggestions(routing, mcpNudge) {
  if (!routing.skills.length) return true;
  if (!mcpNudge || (mcpNudge.mode !== "strong" && mcpNudge.mode !== "escalate"))
    return false;
  if (
    !["docs", "oss-patterns", "history", "local-system"].includes(
      routing.intent.key,
    )
  )
    return false;
  return !routing.skills[0]?.triggerMatched;
}

function shouldSuppressMcpSuggestions(routing, skillNudge) {
  if (!routing.mcps.length) return true;
  const topMcp = routing.mcps[0];
  if (
    routing.intent.key === "reasoning" &&
    topMcp?.name === "thinking" &&
    skillNudge &&
    skillNudge.mode !== "soft"
  ) {
    return true;
  }
  return false;
}

function buildRecommendedMcpLines(mcps) {
  if (!mcps.length) return [];

  return [
    "Suggested MCP tools for this task:",
    ...mcps.map((mcp) => `- \`${mcp.name}_*\`: ${mcp.reason}`),
    "",
  ];
}

function buildMcpGateLines(mcps, mcpNudge) {
  const topMcp = mcps[0];
  if (!topMcp) return [];
  if (!mcpNudge || (mcpNudge.mode !== "strong" && mcpNudge.mode !== "escalate"))
    return [];

  return [
    "### MCP Gate",
    mcpNudge.mode === "escalate"
      ? `- The same high-confidence MCP keeps matching this task. Use \`${topMcp.name}_*\` now unless you have a concrete reason not to.`
      : `- A high-confidence MCP match exists. Before manual workaround or ad-hoc external lookup, decide whether to use \`${topMcp.name}_*\`.`,
    "- Default for external docs, public code search, durable history, relay orchestration, or web fetch tasks: use the best-matching MCP first unless it is clearly unnecessary.",
    "",
  ];
}

function buildEvomemoryPriorityLines(mcpNames, routing, config) {
  if (!config.emphasizeEvomemory) return [];
  if (!mcpNames.includes("evomemory")) return [];
  if (!routing.mcps.some((mcp) => mcp.name === "evomemory")) return [];

  return [
    "### EvoMemory Priority",
    "- Use `evomemory_search_context` early for non-trivial project learning, audits, architecture decisions, or cross-file changes when prior decisions or stable constraints may matter.",
    "- Use `evomemory_record_feedback` for durable corrections, but treat current files and current docs as the source of truth for implementation facts.",
    "",
  ];
}

function buildGuardrailLines(routing) {
  const lines = [];

  if (
    routing.nativeTools.some((tool) =>
      ["glob", "grep", "read"].includes(tool.name),
    )
  ) {
    lines.push(
      "- Prefer workspace read/search tools over `bash` for simple repository search or file-reading work.",
    );
  }

  if (routing.mcps.length) {
    lines.push(
      "- MCP tools help with external or persistent context; they do not replace reading current code or current docs.",
    );
  }

  if (!lines.length) return [];

  return ["### Guardrails", ...lines, ""];
}

function buildInstruction({
  mcpCatalog,
  reusableSkills,
  routing,
  includeVisibleMcpAppendix,
  config,
  skillNudge,
  mcpNudge,
}) {
  const mcpNames = mcpCatalog.map((entry) => entry.name);
  const suppressSkillSuggestions = shouldSuppressSkillSuggestions(
    routing,
    mcpNudge,
  );
  const suppressMcpSuggestions = shouldSuppressMcpSuggestions(
    routing,
    skillNudge,
  );
  const reusableMcps =
    mcpNudge?.mode === "recent" ? [mcpNudge.topMcp.name] : [];
  const renderedMcps =
    suppressMcpSuggestions || mcpNudge?.mode === "recent" ? [] : routing.mcps;

  return [
    MARKER,
    "Silent routing note for the assistant. Do not mention it unless the user asks.",
    "Follow explicit user instructions first.",
    "",
    ...buildToolMappingLines(),
    ...buildEvomemoryPriorityLines(mcpNames, routing, config),
    "### Current Task Routing",
    `- Detected intent: \`${routing.intent.label}\``,
    `- Summary: ${routing.summary}`,
    "- Use only the tools or skills that materially help, and reuse already-loaded skills when they still fit.",
    "",
    ...(suppressSkillSuggestions
      ? []
      : buildSkillLines(routing.skills, skillNudge)),
    ...buildReusableSkillLines(reusableSkills),
    ...buildNativeToolLines(routing.nativeTools),
    ...buildReusableMcpLines(reusableMcps),
    ...buildMcpGateLines(renderedMcps, mcpNudge),
    ...buildRecommendedMcpLines(renderedMcps),
    ...buildGuardrailLines(routing),
    ...(includeVisibleMcpAppendix
      ? [
          "Visible MCP tools from local config:",
          ...buildMcpSummaryLines(mcpCatalog),
          "",
        ]
      : []),
  ].join("\n");
}

function buildDefinitionNote(toolID) {
  const match = TOOL_DESCRIPTION_HINTS.find((entry) => entry.match(toolID));
  return match ? match.note : null;
}

function buildGuardrailError(guardedCommand) {
  const guidance =
    BASH_GUARDRAIL_MESSAGES[guardedCommand] ||
    "Use a dedicated workspace tool instead of `bash` for this operation.";
  return `Prefer the dedicated workspace tool instead of bash for this operation. ${guidance}`;
}

export const ToolForcedEvalPlugin = async ({
  client,
  directory,
  worktree,
  configOverrides,
} = {}) => {
  const reportedConfigIssues = new Set();
  const reportedSkillIssues = new Set();
  const reportedSkillConflicts = new Set();
  const knownMcpToolIDs = new Map();
  const reportConfigIssue = (filePath, error) => {
    if (!error) return;
    const key = `${filePath}:${error.name}:${error.message}`;
    if (reportedConfigIssues.has(key)) return;
    reportedConfigIssues.add(key);
    client?.app
      ?.log?.({
        body: {
          service: "tool-forced-eval",
          level: "warn",
          message: "Failed to read config file",
          extra: {
            filePath,
            error: String(error),
          },
        },
      })
      .catch(() => {});
  };
  const reportSkillIssue = (filePath, error) => {
    if (!error) return;
    const key = `${filePath}:${error.name}:${error.message}`;
    if (reportedSkillIssues.has(key)) return;
    reportedSkillIssues.add(key);
    client?.app
      ?.log?.({
        body: {
          service: "tool-forced-eval",
          level: "warn",
          message: "Failed to read skill file",
          extra: {
            filePath,
            error: String(error),
          },
        },
      })
      .catch(() => {});
  };
  const reportSkillConflict = ({ name, keptPath, ignoredPath }) => {
    const key = `${name}:${keptPath}:${ignoredPath}`;
    if (reportedSkillConflicts.has(key)) return;
    reportedSkillConflicts.add(key);
    client?.app
      ?.log?.({
        body: {
          service: "tool-forced-eval",
          level: "warn",
          message: "Ignored duplicate skill name",
          extra: {
            skillName: name,
            keptPath,
            ignoredPath,
          },
        },
      })
      .catch(() => {});
  };

  const config = loadPluginConfig(configOverrides, reportConfigIssue);
  const initialResolvedConfig = loadCachedMergedOpenCodeConfig(
    directory,
    worktree,
    reportConfigIssue,
  );
  const initialAgentName = resolveAgentName({}, initialResolvedConfig);
  const visibleMcpCatalog = loadVisibleMcpCatalog(
    initialResolvedConfig,
    initialAgentName,
    knownMcpToolIDs,
  );
  const sessionStates = new Map();

  await client?.app
    ?.log?.({
      body: {
        service: "tool-forced-eval",
        level: "info",
        message: "Plugin initialized",
        extra: {
          agentName: initialAgentName,
          visibleMcpNames: visibleMcpCatalog.map((entry) => entry.name),
          config,
        },
      },
    })
    .catch(() => {});

  return {
    event: async ({ event }) => {
      if (event.type === "session.deleted") {
        const sessionID = event.properties?.info?.id;
        if (!sessionID) return;
        sessionStates.delete(sessionID);
        return;
      }

      if (event.type !== "session.compacted") return;

      const sessionID = event.properties?.sessionID;
      if (!sessionID) return;

      const state = getSessionState(sessionStates, sessionID);
      resetForCompaction(state);
    },

    "chat.message": async (input, output) => {
      const { sessionID } = input;
      const userText = collectText(output.parts);
      if (!sessionID) return;

      const state = getSessionState(sessionStates, sessionID);
      const skipReason = getInjectionSkipReason(userText);
      if (skipReason) {
        clearInstruction(state);
        await client?.app
          ?.log?.({
            body: {
              service: "tool-forced-eval",
              level: "debug",
              message: "Skipped task routing guidance",
              extra: {
                sessionID,
                skipReason,
              },
            },
          })
          .catch(() => {});
        return;
      }

      state.turn += 1;
      const currentResolvedConfig = loadCachedMergedOpenCodeConfig(
        directory,
        worktree,
        reportConfigIssue,
      );
      const currentAgentName = resolveAgentName(input, currentResolvedConfig);
      const currentVisibleMcpCatalog = loadVisibleMcpCatalog(
        currentResolvedConfig,
        currentAgentName,
        knownMcpToolIDs,
      );
      const currentSkillCatalog = loadSkillCatalog(
        buildSkillLookupRoots({
          globalConfigDir: getGlobalConfigDir(),
          directory,
          worktree,
          homeDir: process.env.HOME || "",
          customConfigDir: process.env.OPENCODE_CONFIG_DIR
            ? path.resolve(process.env.OPENCODE_CONFIG_DIR)
            : "",
        }),
        reportSkillIssue,
        reportSkillConflict,
      ).filter((skill) =>
        isSkillAllowed(skill.name, currentResolvedConfig, currentAgentName),
      );
      const reusableSkills = getReusableSkills(state, config);
      const routing = buildTaskRouting(
        userText,
        currentVisibleMcpCatalog,
        config,
        currentSkillCatalog,
      );
      const skillNudge = updateSkillNudgeState(state, routing.skills, config);
      const mcpNudge = updateMcpNudgeState(state, routing.mcps, config);
      const includeVisibleMcpAppendix =
        config.includeVisibleMcpAppendixByDefault ||
        (!routing.intent.clear &&
          config.includeVisibleMcpAppendixOnUnclearIntent);

      setInstructionForTurn(
        state,
        buildInstruction({
          mcpCatalog: currentVisibleMcpCatalog,
          reusableSkills,
          routing,
          includeVisibleMcpAppendix,
          config,
          skillNudge,
          mcpNudge,
        }),
      );

      await client?.app
        ?.log?.({
          body: {
            service: "tool-forced-eval",
            level: "debug",
            message: "Built task routing guidance",
            extra: {
              sessionID,
              agentName: currentAgentName,
              intent: routing.intent.key,
              recommendedSkills: routing.skills.map((skill) => skill.name),
              recommendedMcps: routing.mcps.map((mcp) => mcp.name),
              preferredNativeTools: routing.nativeTools.map(
                (tool) => tool.name,
              ),
            },
          },
        })
        .catch(() => {});
    },

    "experimental.chat.system.transform": async ({ sessionID }, output) => {
      if (!sessionID) return;

      const instruction = sessionStates.get(sessionID)?.instruction;
      if (!instruction) return;
      if (
        output.system.some(
          (block) => typeof block === "string" && block.startsWith(MARKER),
        )
      )
        return;

      output.system.push(instruction);

      await client?.app
        ?.log?.({
          body: {
            service: "tool-forced-eval",
            level: "debug",
            message: "Injected task routing system prompt",
            extra: {
              sessionID,
            },
          },
        })
        .catch(() => {});
    },

    "tool.execute.before": async (input, output) => {
      if (!config.enableBashGuardrails) return;
      if (input.tool !== "bash") return;
      if (config.bashGuardrailMode !== "error") return;

      const guardedCommand = findGuardedBashCommand(
        getBashCommand(input, output),
        config.guardedBashCommands,
      );
      if (!guardedCommand) return;

      await client?.app
        ?.log?.({
          body: {
            service: "tool-forced-eval",
            level: "debug",
            message: "Blocked guarded bash command",
            extra: {
              sessionID: input.sessionID,
              guardrailReason: guardedCommand,
            },
          },
        })
        .catch(() => {});

      throw new Error(buildGuardrailError(guardedCommand));
    },

    "tool.execute.after": async (input) => {
      const sessionID = input.sessionID;
      if (!sessionID) return;

      const state = getSessionState(sessionStates, sessionID);
      if (input.tool === "skill") {
        const skillName =
          typeof input.args?.name === "string" ? input.args.name.trim() : "";
        if (!skillName) return;
        recordSkillLoad(state, skillName);
        return;
      }
      if (isBuiltinToolID(input.tool)) return;

      const resolvedConfig = loadCachedMergedOpenCodeConfig(
        directory,
        worktree,
        reportConfigIssue,
      );
      const mcpName = resolveMcpNameFromToolID(
        input.tool,
        resolvedConfig,
        knownMcpToolIDs,
      );
      if (!mcpName) return;
      recordMcpUse(state, mcpName);
    },

    "tool.definition": async ({ toolID }, output) => {
      const note = buildDefinitionNote(toolID);
      if (!note && isBuiltinToolID(toolID)) return;

      if (!isBuiltinToolID(toolID)) {
        const resolvedConfig = loadCachedMergedOpenCodeConfig(
          directory,
          worktree,
          reportConfigIssue,
        );
        rememberKnownMcpToolID(toolID, resolvedConfig, knownMcpToolIDs);
      }

      if (!note) return;

      const currentDescription =
        typeof output.description === "string" ? output.description : "";
      if (currentDescription.includes(note)) return;
      output.description = currentDescription
        ? `${currentDescription}\n\nPlugin guidance: ${note}`
        : `Plugin guidance: ${note}`;
    },
  };
};

export default {
  id: "tool-forced-eval",
  server: ToolForcedEvalPlugin,
};
