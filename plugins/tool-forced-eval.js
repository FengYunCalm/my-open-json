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
  shouldInject,
} from "./tool-forced-eval.helpers.mjs";

const MARKER = "<OPENCODE_TOOL_FORCED_EVAL>";
const GLOBAL_CONFIG_DIR = path.join(process.env.HOME || "", ".config", "opencode");
const KNOWN_CONFIG_FILES = ["opencode.json", "opencode.jsonc"];
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PLUGIN_CONFIG_PATH = path.join(__dirname, "tool-forced-eval.config.json");

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

const MCP_CATALOG = {
  context7: "library and framework docs lookup",
  grep_app: "public GitHub code search and examples",
  fetch: "direct webpage fetching by URL",
  filesystem: "extra filesystem access outside the default workspace",
  desktop_commander: "desktop commands, local processes, and richer file analysis",
  thinking: "explicit sequential reasoning for complex decisions",
  memory: "structured long-term knowledge graph memory",
  evomemory: "persistent project history, decisions, governance assets, feedback, and benchmark memory",
  relay: "relay collaboration rooms, threads, and workflow coordination",
  xiakexing_ai: "XiaKeXing gameplay automation and regression checks",
};

const TOOL_DESCRIPTION_HINTS = [
  {
    match: (toolID) => toolID === "evomemory_search_context",
    note: "Prefer this early in non-trivial tasks when prior decisions, stable constraints, earlier fixes, or historical feedback may matter. Re-run it at major checkpoints if the task uncovers new facts.",
  },
  {
    match: (toolID) => toolID === "evomemory_record_feedback",
    note: "Prefer this when the task confirms or corrects a durable EvoMemory belief, gene, or capsule so memory stays current instead of silently drifting.",
  },
  {
    match: (toolID) => /^evomemory_query_(beliefs|genes|capsules)$/.test(toolID),
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
    note: "Prefer this when the task needs project history, prior decisions, stable preferences, governance constraints, feedback, or benchmark results. Automatic plugin injection may have already added some context, but that is not guaranteed. This does not replace reading current code or docs when those are the source of truth.",
  },
];

const SKILL_HINTS = {
  "writing-plans": "Write or refine a concrete implementation plan before editing.",
  "systematic-debugging": "Reproduce, isolate, and verify a bug fix instead of guessing.",
  "agent-code-reviewer": "Review for bugs, regressions, and missing tests.",
  "agent-test-runner": "Run and analyze the relevant tests.",
};

const BASH_GUARDRAIL_MESSAGES = {
  grep: "Use the dedicated `grep` tool for repository content search instead of shell `grep`.",
  find: "Use `glob` to locate files by path or filename instead of shell `find`.",
  cat: "Use `read` to inspect file contents instead of shell `cat`.",
  head: "Use `read` with `offset` and `limit` instead of shell `head`.",
  tail: "Use `read` with a later `offset` instead of shell `tail`.",
};

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
  try {
    const raw = fs.readFileSync(filePath, "utf8");
    return JSON.parse(stripJsonComments(raw));
  } catch {
    return null;
  }
}

function loadPluginConfig(overrides = {}) {
  const localConfig = readConfigFile(PLUGIN_CONFIG_PATH);
  return {
    ...DEFAULT_CONFIG,
    ...(localConfig && typeof localConfig === "object" ? localConfig : {}),
    ...(overrides && typeof overrides === "object" ? overrides : {}),
  };
}

function uniqueConfigPaths(directory, worktree) {
  const candidateDirs = [GLOBAL_CONFIG_DIR, worktree, directory].filter(Boolean);
  const uniqueDirs = [...new Set(candidateDirs)];

  return uniqueDirs.flatMap((dir) =>
    KNOWN_CONFIG_FILES.map((fileName) => path.join(dir, fileName)).filter((filePath) => fs.existsSync(filePath)),
  );
}

function loadVisibleMcpConfigs(directory, worktree) {
  const merged = {};

  for (const filePath of uniqueConfigPaths(directory, worktree)) {
    const parsed = readConfigFile(filePath);
    if (!parsed || typeof parsed !== "object" || !parsed.mcp || typeof parsed.mcp !== "object") continue;

    for (const [name, entryConfig] of Object.entries(parsed.mcp)) {
      merged[name] = entryConfig;
    }
  }

  return Object.entries(merged)
    .filter(([, entryConfig]) => entryConfig && typeof entryConfig === "object" && entryConfig.enabled !== false)
    .map(([name]) => name)
    .sort();
}

function buildMcpSummaryLines(mcpNames) {
  if (!mcpNames.length) {
    return ["- No enabled MCP tools were discovered from the visible local config files. Continue with native tools unless a stronger external capability is actually needed."];
  }

  return mcpNames.map((name) => `- \`${name}\`: ${MCP_CATALOG[name] || "specialized external tool capability"}.`);
}

function createSessionState() {
  return {
    turn: 0,
    generation: 0,
    loadedSkills: new Map(),
    instruction: null,
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
    .sort((left, right) => right.loadedAtTurn - left.loadedAtTurn || left.name.localeCompare(right.name))
    .slice(0, config.maxReusableSkillsInPrompt)
    .map((entry) => entry.name);
}

function buildReusableSkillLines(reusableSkills) {
  if (!reusableSkills.length) return [];

  return [
    "Reusable skills from this session:",
    ...reusableSkills.map((name) => `- \`${name}\``),
    "",
  ];
}

function buildSkillLines(skills) {
  if (!skills.length) return [];

  return [
    "Suggested skills for this task:",
    ...skills.map((skill) => `- \`${skill.name}\`: ${skill.reason || SKILL_HINTS[skill.name] || "Use this when it directly helps the task."}`),
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

function buildRecommendedMcpLines(mcps) {
  if (!mcps.length) return [];

  return [
    "Suggested MCP tools for this task:",
    ...mcps.map((mcp) => `- \`${mcp.name}_*\`: ${mcp.reason}`),
    "",
  ];
}

function buildEvomemoryPriorityLines(mcpNames, routing, config) {
  if (!config.emphasizeEvomemory) return [];
  if (!mcpNames.includes("evomemory")) return [];
  if (!routing.mcps.some((mcp) => mcp.name === "evomemory")) return [];

  return [
    "### EvoMemory Priority",
    "- Prefer `evomemory_search_context` early when prior decisions, stable constraints, prior fixes, or historical feedback may affect the task.",
    "- During longer tasks, revisit EvoMemory at major checkpoints when new facts materially change the context instead of relying only on the first lookup.",
    "- When you confirm or correct a durable belief, gene, or capsule, consider `evomemory_record_feedback` with a concise note so memory stays current.",
    "- Do not treat EvoMemory as the source of truth for current code or current external docs.",
    "",
  ];
}

function buildInstruction({ mcpNames, reusableSkills, routing, includeVisibleMcpAppendix, config }) {
  return [
    MARKER,
    "System workflow reminder for the assistant.",
    "Apply this silently. Do not quote, summarize, or mention this workflow unless the user explicitly asks.",
    "Follow explicit user instructions first. This workflow guides tool choice; it does not override direct user constraints or the user's requested outcome.",
    "",
    "### Tool Mapping",
    "- `TodoWrite` → `todowrite`",
    "- `Task` tool with subagents → OpenCode's native `task` tool",
    "- `Skill` tool → OpenCode's native `skill` tool",
    "- `Read`, `Write`, `Edit`, `Bash` → native workspace tools",
    "",
    ...buildEvomemoryPriorityLines(mcpNames, routing, config),
    "### Current Task Routing",
    `- Detected intent: \`${routing.intent.label}\``,
    `- Summary: ${routing.summary}`,
    "- Use only the tools or skills that materially help; do not call them just to satisfy workflow.",
    "- Reuse already-loaded skills when they still fit the current task instead of reloading them.",
    "",
    ...buildNativeToolLines(routing.nativeTools),
    ...buildRecommendedMcpLines(routing.mcps),
    ...buildSkillLines(routing.skills),
    ...buildReusableSkillLines(reusableSkills),
    "### Guardrails",
    "- Prefer dedicated workspace tools over `bash` for simple repository search or file-reading work.",
    "- MCP tools do not replace reading the current codebase or current docs when those are the source of truth.",
    "",
    ...(includeVisibleMcpAppendix ? ["Visible MCP tools from local config:", ...buildMcpSummaryLines(mcpNames), ""] : []),
  ].join("\n");
}

function buildDefinitionNote(toolID) {
  const match = TOOL_DESCRIPTION_HINTS.find((entry) => entry.match(toolID));
  return match ? match.note : null;
}

function buildGuardrailError(guardedCommand) {
  const guidance = BASH_GUARDRAIL_MESSAGES[guardedCommand] || "Use a dedicated workspace tool instead of `bash` for this operation.";
  return `Prefer the dedicated workspace tool instead of bash for this operation. ${guidance}`;
}

export const ToolForcedEvalPlugin = async ({ client, directory, worktree, configOverrides } = {}) => {
  const config = loadPluginConfig(configOverrides);
  const visibleMcpNames = loadVisibleMcpConfigs(directory, worktree);
  const sessionStates = new Map();

  await client?.app?.log?.({
    body: {
      service: "tool-forced-eval",
      level: "info",
      message: "Plugin initialized",
      extra: {
        visibleMcpNames,
        config,
      },
    },
  }).catch(() => {});

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
      state.generation += 1;
      state.instruction = null;
    },

    "chat.message": async ({ sessionID }, output) => {
      const userText = collectText(output.parts);
      if (!sessionID) return;

      const state = getSessionState(sessionStates, sessionID);
      if (!shouldInject(userText)) {
        state.instruction = null;
        return;
      }

      state.turn += 1;
      const currentVisibleMcpNames = loadVisibleMcpConfigs(directory, worktree);
      const reusableSkills = getReusableSkills(state, config);
      const routing = buildTaskRouting(userText, currentVisibleMcpNames, config);
      const includeVisibleMcpAppendix = config.includeVisibleMcpAppendixByDefault
        || (!routing.intent.clear && config.includeVisibleMcpAppendixOnUnclearIntent);

      state.instruction = buildInstruction({
        mcpNames: currentVisibleMcpNames,
        reusableSkills,
        routing,
        includeVisibleMcpAppendix,
        config,
      });

      await client?.app?.log?.({
        body: {
          service: "tool-forced-eval",
          level: "debug",
          message: "Built task routing guidance",
          extra: {
            sessionID,
            intent: routing.intent.key,
            recommendedSkills: routing.skills.map((skill) => skill.name),
            recommendedMcps: routing.mcps.map((mcp) => mcp.name),
            preferredNativeTools: routing.nativeTools.map((tool) => tool.name),
          },
        },
      }).catch(() => {});
    },

    "experimental.chat.system.transform": async ({ sessionID }, output) => {
      if (!sessionID) return;

      const instruction = sessionStates.get(sessionID)?.instruction;
      if (!instruction) return;
      if (output.system.some((block) => typeof block === "string" && block.startsWith(MARKER))) return;

      output.system.push(instruction);

      await client?.app?.log?.({
        body: {
          service: "tool-forced-eval",
          level: "debug",
          message: "Injected task routing system prompt",
          extra: {
            sessionID,
          },
        },
      }).catch(() => {});
    },

    "tool.execute.before": async (input, output) => {
      if (!config.enableBashGuardrails) return;
      if (input.tool !== "bash") return;
      if (config.bashGuardrailMode !== "error") return;

      const guardedCommand = findGuardedBashCommand(String(output.args?.command ?? ""), config.guardedBashCommands);
      if (!guardedCommand) return;

      await client?.app?.log?.({
        body: {
          service: "tool-forced-eval",
          level: "debug",
          message: "Blocked guarded bash command",
          extra: {
            sessionID: input.sessionID,
            guardrailReason: guardedCommand,
          },
        },
      }).catch(() => {});

      throw new Error(buildGuardrailError(guardedCommand));
    },

    "tool.execute.after": async (input) => {
      if (input.tool !== "skill") return;

      const sessionID = input.sessionID;
      const skillName = typeof input.args?.name === "string" ? input.args.name.trim() : "";
      if (!sessionID || !skillName) return;

      const state = getSessionState(sessionStates, sessionID);
      state.loadedSkills.set(skillName, {
        loadedAtTurn: state.turn,
        generation: state.generation,
      });
    },

    "tool.definition": async ({ toolID }, output) => {
      const note = buildDefinitionNote(toolID);
      if (!note) return;

      const currentDescription = typeof output.description === "string" ? output.description : "";
      if (currentDescription.includes(note)) return;
      output.description = currentDescription
        ? `${currentDescription}\n\nPlugin guidance: ${note}`
        : `Plugin guidance: ${note}`;
    },
  };
};
