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
  {
    match: (toolID) => toolID.startsWith("relay_") || toolID.startsWith("mcp__relay__"),
    note: "Prefer this only when the task explicitly needs relay rooms, threads, durable messages, or relay-backed team coordination.",
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

function buildInstruction(mcpNames) {
  return [
    MARKER,
    "## Required: Skill and MCP evaluation workflow",
    "",
    "Before answering the current user request, complete this workflow:",
    "",
    "### Step 1 - Evaluate skills",
    "- Decide whether any locally installed skill applies.",
    "- Prioritize process skills, debugging skills, project-specific skills, and framework/domain skills.",
    "- If there is even a 1 percent chance that a skill applies, you must call the skill tool.",
    "",
    "### Step 2 - Evaluate MCP",
    "- Decide whether any enabled MCP tool is a better fit than answering from memory or using only built-in tools.",
    "- Prefer MCP when the task needs external docs, public code examples, direct URL retrieval, richer filesystem access, explicit reasoning, memory systems, or project-specific automation.",
    "- If a matching MCP applies, call it before giving conclusions.",
    "",
    "Visible MCP tools from local config:",
    ...buildMcpSummaryLines(mcpNames),
    "",
    "### Step 3 - Activate",
    "- If any skill applies: call the skill tool immediately.",
    "- If no skill applies: explicitly state that no suitable skill was found, then continue.",
    "- If any MCP is a clear fit: call the MCP tool before answering.",
    "- If no MCP fits: continue with the normal toolset without forcing MCP usage.",
    "",
    "### Step 4 - Execute",
    "- Only after the skill and MCP checks are complete may you analyze, implement, modify files, run commands, or give conclusions.",
    "- Do not skip these checks and answer directly.",
    "",
    "### Extra rules",
    "- For implementation, debugging, planning, review, testing, specification, refactoring, docs lookup, or research tasks, default to checking skills first and MCP second.",
    "- Use MCP when it clearly improves correctness or freshness, but do not use it performatively.",
    "- You may skip this workflow only for slash commands or obvious tiny social messages.",
    "",
  ].join("\n");
}

function buildDefinitionNote(toolID) {
  const match = TOOL_DESCRIPTION_HINTS.find((entry) => entry.match(toolID));
  return match ? match.note : null;
}

export const ToolForcedEvalPlugin = async ({ client, directory, worktree }) => {
  const visibleMcpNames = loadVisibleMcpConfigs(directory, worktree);

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
    "experimental.chat.messages.transform": async (_input, output) => {
      const userMessages = output.messages.filter((message) => message.info.role === "user");
      const target = userMessages.at(-1);
      if (!target || !target.parts.length) return;

      const userText = collectText(target.parts);
      if (!shouldInject(userText)) return;

      const ref = target.parts[0];
      target.parts.unshift({
        ...ref,
        type: "text",
        text: buildInstruction(visibleMcpNames),
      });

      await client?.app?.log?.({
        body: {
          service: "tool-forced-eval",
          level: "debug",
          message: "Injected forced skill and MCP evaluation prompt",
          extra: {
            preview: userText.slice(0, 120),
          },
        },
      }).catch(() => {});
    },

    "tool.definition": async ({ toolID }, output) => {
      const note = buildDefinitionNote(toolID);
      if (!note) return;
      if (output.description.includes(note)) return;

      output.description = `${output.description}\n\nPlugin guidance: ${note}`;
    },
  };
};
