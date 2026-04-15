/**
 * Force explicit evaluation of skills and applicable MCP tools before the
 * model starts answering or implementing.
 */

import fs from "fs";
import path from "path";

const MARKER = "<OPENCODE_TOOL_FORCED_EVAL>";
const LEGACY_MARKER = "<OPENCODE_SKILL_FORCED_EVAL>";
const GLOBAL_CONFIG_DIR = path.join(process.env.HOME || "", ".config", "opencode");
const KNOWN_CONFIG_FILES = ["opencode.json", "opencode.jsonc"];
const SKILL_REUSE_TTL = 3;

const MCP_CATALOG = {
  context7: "library and framework docs lookup",
  grep_app: "public GitHub code search and examples",
  fetch: "direct webpage fetching by URL",
  filesystem: "extra filesystem access outside the default workspace",
  desktop_commander: "desktop commands, local processes, and richer file analysis",
  thinking: "explicit sequential reasoning for complex decisions",
  memory: "structured long-term knowledge graph memory",
  mempalace: "local knowledge base and entity recall",
  relay: "relay collaboration rooms, threads, and workflow coordination",
  xiakexing_ai: "XiaKeXing gameplay automation and regression checks",
};

const TOOL_DESCRIPTION_HINTS = [
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
    match: (toolID) => toolID.startsWith("mempalace_"),
    note: "Prefer this when the task needs knowledge already stored in the local MemPalace, such as prior decisions, project facts, or historical context.",
  },
];

function collectText(parts) {
  return parts
    .filter((part) => part.type === "text" && typeof part.text === "string")
    .map((part) => part.text)
    .join("\n")
    .trim();
}

function isLikelySlashCommand(text) {
  const firstToken = text.trim().split(/\s+/)[0] || "";
  return /^\/[^/\s]+$/.test(firstToken);
}

function isLikelySmallTalk(text) {
  const normalized = text.trim().toLowerCase();
  if (!normalized) return true;
  if (normalized.length > 24) return false;

  const patterns = [
    /^hi$/,
    /^hello$/,
    /^hey$/,
    /^thanks?$/,
    /^thank you$/,
    /^ok$/,
    /^okay$/,
    /^continue$/,
    /^start$/,
    /^go$/,
    /^yes$/,
    /^no$/,
  ];

  return patterns.some((pattern) => pattern.test(normalized));
}

function shouldInject(text) {
  if (!text) return false;
  if (text.includes(MARKER) || text.includes(LEGACY_MARKER)) return false;
  if (isLikelySlashCommand(text)) return false;
  if (isLikelySmallTalk(text)) return false;
  return true;
}

function stripJsonComments(raw) {
  return raw
    .replace(/^\uFEFF/, "")
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/(^|[^:\\])\/\/.*$/gm, "$1");
}

function readConfigFile(filePath) {
  try {
    const raw = fs.readFileSync(filePath, "utf8");
    return JSON.parse(stripJsonComments(raw));
  } catch {
    return null;
  }
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

    for (const [name, config] of Object.entries(parsed.mcp)) {
      merged[name] = config;
    }
  }

  return Object.entries(merged)
    .filter(([, config]) => config && typeof config === "object" && config.enabled !== false)
    .map(([name]) => name)
    .sort();
}

function buildMcpSummaryLines(mcpNames) {
  if (!mcpNames.length) {
    return ["- No enabled MCP tools were discovered from the visible local config files. Still evaluate whether an available MCP tool would be more appropriate than answering directly."];
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

function getReusableSkills(state) {
  const reusable = [];

  for (const [name, record] of Array.from(state.loadedSkills.entries())) {
    const sameGeneration = record.generation === state.generation;
    const withinTtl = state.turn - record.loadedAtTurn <= SKILL_REUSE_TTL;

    if (sameGeneration && withinTtl) {
      reusable.push(name);
      continue;
    }

    state.loadedSkills.delete(name);
  }

  return reusable.sort();
}

function buildReusableSkillLines(reusableSkills) {
  if (!reusableSkills.length) return [];

  return [
    "Currently reusable skills from this session:",
    ...reusableSkills.map((name) => `- \`${name}\``),
    "",
  ];
}

function buildInstruction(mcpNames, reusableSkills) {
  return [
    MARKER,
    "System workflow reminder for the assistant.",
    "Apply this silently. Do not quote, summarize, or mention this workflow unless the user explicitly asks.",
    "Follow explicit user instructions first. This workflow guides tool choice; it does not override direct user constraints.",
    "",
    "### Skills",
    "- Use the core skill catalog as the source of available skills; this reminder only adds local workflow policy.",
    "- If a relevant skill is already reusable in the current context, reuse it instead of loading it again.",
    "- Do not reload the same skill just to satisfy the workflow.",
    "- A previously loaded skill is reusable only within the current context window; after compaction or a clear task shift, reevaluate whether it should be loaded again.",
    "- If there is even a 1 percent chance that a new skill applies, you must call the skill tool.",
    "",
    ...buildReusableSkillLines(reusableSkills),
    "### Tool Mapping",
    "- `TodoWrite` → `todowrite`",
    "- `Task` tool with subagents → OpenCode's native `task` tool",
    "- `Skill` tool → OpenCode's native `skill` tool",
    "- `Read`, `Write`, `Edit`, `Bash` → native workspace tools",
    "",
    "### MCP",
    "- Decide whether any enabled MCP tool applies.",
    "- Prefer MCP when the task needs external docs, public code examples, direct URL retrieval, richer filesystem access, explicit reasoning, memory systems, or project-specific automation.",
    "- If any enabled MCP tool applies, you must call it before giving conclusions.",
    "- If no enabled MCP tool applies, continue with built-in tools without forcing MCP usage.",
    "",
    "Visible MCP tools from local config:",
    ...buildMcpSummaryLines(mcpNames),
    "",
    "### Activation",
    "- If any reusable skill already fits: continue with it instead of reloading.",
    "- If any new skill applies: call the skill tool immediately.",
    "- If any MCP applies: call the MCP tool immediately before answering.",
    "- If no MCP fits: continue with the normal toolset without forcing MCP usage.",
    "",
    "### Execution",
    "- Only after the skill and MCP checks are complete may you analyze, implement, modify files, run commands, or give conclusions.",
    "- Do not skip these checks and answer directly.",
    "- For implementation, debugging, planning, review, testing, specification, refactoring, docs lookup, or research tasks, default to checking skills first and MCP second.",
    "- Skip this workflow only for slash commands or obvious tiny social messages.",
    "",
  ].join("\n");
}

function buildDefinitionNote(toolID) {
  const match = TOOL_DESCRIPTION_HINTS.find((entry) => entry.match(toolID));
  return match ? match.note : null;
}

export const ToolForcedEvalPlugin = async ({ client, directory, worktree }) => {
  const visibleMcpNames = loadVisibleMcpConfigs(directory, worktree);
  const sessionStates = new Map();

  await client?.app?.log?.({
    body: {
      service: "tool-forced-eval",
      level: "info",
      message: "Plugin initialized",
      extra: {
        visibleMcpNames,
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
      state.instruction = buildInstruction(visibleMcpNames, getReusableSkills(state));
    },

    "experimental.chat.system.transform": async ({ sessionID }, output) => {
      if (!sessionID) return;

      const instruction = sessionStates.get(sessionID)?.instruction;
      if (!instruction) return;

      output.system.push(instruction);

      await client?.app?.log?.({
        body: {
          service: "tool-forced-eval",
          level: "debug",
          message: "Injected forced skill and MCP evaluation system prompt",
          extra: {
            sessionID,
          },
        },
      }).catch(() => {});
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
      if (output.description.includes(note)) return;

      output.description = `${output.description}\n\nPlugin guidance: ${note}`;
    },
  };
};
