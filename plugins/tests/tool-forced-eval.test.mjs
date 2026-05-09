import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import { ToolForcedEvalPlugin } from "../tool-forced-eval.js";

const createPlugin = (options = {}) =>
  ToolForcedEvalPlugin({
    client: { app: { log: async () => {} } },
    directory: options.directory ?? "/home/mechrevo/.config/opencode",
    worktree: options.worktree ?? "/home/mechrevo/.config/opencode",
    configOverrides: options.configOverrides,
  });

const createPluginWithLogs = (logs, options = {}) =>
  ToolForcedEvalPlugin({
    client: { app: { log: async (entry) => logs.push(entry.body) } },
    directory: options.directory ?? "/home/mechrevo/.config/opencode",
    worktree: options.worktree ?? "/home/mechrevo/.config/opencode",
    configOverrides: options.configOverrides,
  });

function writeSkill(skillRoot, name, description) {
  const dir = path.join(skillRoot, name);
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(
    path.join(dir, "SKILL.md"),
    `---\nname: ${name}\ndescription: ${description}\n---\n`,
  );
}

async function withEnv(overrides, fn) {
  const previous = new Map();

  for (const [key, value] of Object.entries(overrides)) {
    previous.set(key, process.env[key]);
    if (value === undefined || value === null || value === "") {
      delete process.env[key];
      continue;
    }
    process.env[key] = value;
  }

  try {
    return await fn();
  } finally {
    for (const [key, value] of previous.entries()) {
      if (value === undefined) {
        delete process.env[key];
        continue;
      }
      process.env[key] = value;
    }
  }
}

test("injects routed tool-forced-eval guidance through system transform", async () => {
  const plugin = await createPlugin();

  await plugin["chat.message"](
    { sessionID: "session-system-prompt" },
    {
      message: { parts: [] },
      parts: [{ type: "text", text: "学习一下 tool-forced-eval 这个插件源码" }],
    },
  );

  const output = { system: [] };
  await plugin["experimental.chat.system.transform"](
    { sessionID: "session-system-prompt", model: {} },
    output,
  );

  const injected = output.system.at(-1) ?? "";

  assert.match(injected, /^<OPENCODE_TOOL_FORCED_EVAL>/);
  assert.match(injected, /Silent routing note for the assistant\./);
  assert.match(injected, /Follow explicit user instructions first\./);
  assert.match(injected, /Tool mapping:/);
  assert.match(injected, /### Current Task Routing/);
  assert.match(injected, /Detected intent: `local-code`/);
  assert.match(
    injected,
    /Inspect current code with native tools, and use EvoMemory for prior decisions or stable constraints before project learning, audit, or architecture conclusions\./,
  );
  assert.match(injected, /Preferred native tools right now:/);
  assert.match(injected, /- `glob`: Find files by name or path pattern\./);
  assert.match(
    injected,
    /- `grep`: Search repository contents for symbols, strings, or patterns\./,
  );
  assert.match(
    injected,
    /- `read`: Open only the relevant files and sections\./,
  );
  assert.match(injected, /### Guardrails/);
  assert.match(
    injected,
    /Prefer workspace read\/search tools over `bash` for simple repository search or file-reading work\./,
  );
  assert.match(injected, /### EvoMemory Priority/);
  assert.match(injected, /`evomemory_\*`/);
  assert.doesNotMatch(injected, /Visible MCP tools from local config:/);
  assert.doesNotMatch(injected, /must call the skill tool/i);
  assert.doesNotMatch(injected, /call the MCP tool immediately/i);
});

test("skips system prompt injection for slash commands", async () => {
  const plugin = await createPlugin();

  await plugin["chat.message"](
    { sessionID: "session-slash-command" },
    {
      message: { parts: [] },
      parts: [{ type: "text", text: "/review" }],
    },
  );

  const output = { system: [] };
  await plugin["experimental.chat.system.transform"](
    { sessionID: "session-slash-command", model: {} },
    output,
  );

  assert.equal(output.system.length, 0);
});

test("logs why task routing guidance was skipped", async () => {
  const logs = [];
  const plugin = await createPluginWithLogs(logs);

  for (const [sessionID, text] of [
    ["session-skip-slash", "/review"],
    ["session-skip-small-talk", "ok"],
    ["session-skip-marker", "please do not repeat <OPENCODE_TOOL_FORCED_EVAL>"],
  ]) {
    await plugin["chat.message"](
      { sessionID },
      {
        message: { parts: [] },
        parts: [{ type: "text", text }],
      },
    );
  }

  const skippedLogs = logs.filter(
    (entry) => entry.message === "Skipped task routing guidance",
  );
  assert.equal(skippedLogs.length, 3);
  assert.deepEqual(skippedLogs.map((entry) => entry.extra?.skipReason).sort(), [
    "marker-echo",
    "slash-command",
    "small-talk",
  ]);
});

test("skips system prompt injection for tiny english and chinese small-talk plus marker echoes", async () => {
  const plugin = await createPlugin();

  await plugin["chat.message"](
    { sessionID: "session-small-talk-en" },
    {
      message: { parts: [] },
      parts: [{ type: "text", text: "ok" }],
    },
  );

  const englishOutput = { system: [] };
  await plugin["experimental.chat.system.transform"](
    { sessionID: "session-small-talk-en", model: {} },
    englishOutput,
  );
  assert.equal(englishOutput.system.length, 0);

  await plugin["chat.message"](
    { sessionID: "session-small-talk-zh" },
    {
      message: { parts: [] },
      parts: [{ type: "text", text: "好的" }],
    },
  );

  const chineseOutput = { system: [] };
  await plugin["experimental.chat.system.transform"](
    { sessionID: "session-small-talk-zh", model: {} },
    chineseOutput,
  );
  assert.equal(chineseOutput.system.length, 0);

  await plugin["chat.message"](
    { sessionID: "session-substantive-zh" },
    {
      message: { parts: [] },
      parts: [{ type: "text", text: "继续分析这个实现" }],
    },
  );

  const substantiveOutput = { system: [] };
  await plugin["experimental.chat.system.transform"](
    { sessionID: "session-substantive-zh", model: {} },
    substantiveOutput,
  );
  assert.equal(substantiveOutput.system.length, 1);

  await plugin["chat.message"](
    { sessionID: "session-small-talk-zh" },
    {
      message: { parts: [] },
      parts: [
        {
          type: "text",
          text: "please do not repeat <OPENCODE_TOOL_FORCED_EVAL>",
        },
      ],
    },
  );

  const markerOutput = { system: [] };
  await plugin["experimental.chat.system.transform"](
    { sessionID: "session-small-talk-zh", model: {} },
    markerOutput,
  );
  assert.equal(markerOutput.system.length, 0);
});

test("routes history, docs, and GitHub pattern tasks to the right MCP shortlists", async () => {
  const plugin = await createPlugin();

  await plugin["chat.message"](
    { sessionID: "session-memory-maintenance" },
    {
      message: { parts: [] },
      parts: [
        {
          type: "text",
          text: "use evomemory_record_feedback to correct stale beliefs after this task",
        },
      ],
    },
  );
  const maintenanceOutput = { system: [] };
  await plugin["experimental.chat.system.transform"](
    { sessionID: "session-memory-maintenance", model: {} },
    maintenanceOutput,
  );
  const maintenanceInjected = maintenanceOutput.system.at(-1) ?? "";
  assert.match(maintenanceInjected, /### EvoMemory Priority/);
  assert.match(maintenanceInjected, /Detected intent: `memory-maintenance`/);
  assert.match(
    maintenanceInjected,
    /Use EvoMemory to inspect existing context and keep durable memory current as the task confirms, corrects, or reconciles prior state\./,
  );
  assert.match(maintenanceInjected, /`evomemory_\*`/);

  await plugin["chat.message"](
    { sessionID: "session-history" },
    {
      message: { parts: [] },
      parts: [
        {
          type: "text",
          text: "review prior project decisions about tool-forced-eval",
        },
      ],
    },
  );
  const historyOutput = { system: [] };
  await plugin["experimental.chat.system.transform"](
    { sessionID: "session-history", model: {} },
    historyOutput,
  );
  const historyInjected = historyOutput.system.at(-1) ?? "";
  assert.match(historyInjected, /### EvoMemory Priority/);
  assert.match(historyInjected, /Detected intent: `history`/);
  assert.match(historyInjected, /Suggested MCP tools for this task:/);
  assert.match(historyInjected, /`evomemory_\*`/);
  assert.doesNotMatch(historyInjected, /`context7_\*`/);

  await plugin["chat.message"](
    { sessionID: "session-docs" },
    {
      message: { parts: [] },
      parts: [{ type: "text", text: "look up the React useEffectEvent docs" }],
    },
  );
  const docsOutput = { system: [] };
  await plugin["experimental.chat.system.transform"](
    { sessionID: "session-docs", model: {} },
    docsOutput,
  );
  const docsInjected = docsOutput.system.at(-1) ?? "";
  assert.match(docsInjected, /Detected intent: `docs`/);
  assert.match(docsInjected, /`context7_\*`/);

  await plugin["chat.message"](
    { sessionID: "session-oss" },
    {
      message: { parts: [] },
      parts: [
        { type: "text", text: "go search similar OpenCode plugins on GitHub" },
      ],
    },
  );
  const ossOutput = { system: [] };
  await plugin["experimental.chat.system.transform"](
    { sessionID: "session-oss", model: {} },
    ossOutput,
  );
  const ossInjected = ossOutput.system.at(-1) ?? "";
  assert.match(ossInjected, /Detected intent: `oss-patterns`/);
  assert.match(ossInjected, /`grep_app_\*`/);

  await plugin["chat.message"](
    { sessionID: "session-local-code" },
    {
      message: { parts: [] },
      parts: [
        {
          type: "text",
          text: "please explain the current implementation in plugins/tool-forced-eval.js",
        },
      ],
    },
  );
  const codeOutput = { system: [] };
  await plugin["experimental.chat.system.transform"](
    { sessionID: "session-local-code", model: {} },
    codeOutput,
  );
  const codeInjected = codeOutput.system.at(-1) ?? "";
  assert.match(codeInjected, /Detected intent: `local-code`/);
  assert.match(codeInjected, /- `glob`:/);
  assert.doesNotMatch(codeInjected, /`evomemory_\*`/);

  await plugin["chat.message"](
    { sessionID: "session-nontrivial-code" },
    {
      message: { parts: [] },
      parts: [
        {
          type: "text",
          text: "debug this cross-file regression in the plugin implementation",
        },
      ],
    },
  );
  const nontrivialCodeOutput = { system: [] };
  await plugin["experimental.chat.system.transform"](
    { sessionID: "session-nontrivial-code", model: {} },
    nontrivialCodeOutput,
  );
  const nontrivialCodeInjected = nontrivialCodeOutput.system.at(-1) ?? "";
  assert.match(nontrivialCodeInjected, /Detected intent: `local-code`/);
  assert.match(nontrivialCodeInjected, /### EvoMemory Priority/);
  assert.match(nontrivialCodeInjected, /`evomemory_\*`/);
});

test("only adds tool guidance for MCPs that still opt in", async () => {
  const plugin = await createPlugin();

  const context7Output = { description: "Query docs", parameters: {} };
  await plugin["tool.definition"](
    { toolID: "context7_query-docs" },
    context7Output,
  );
  assert.match(context7Output.description, /Plugin guidance:/);

  const evomemoryOutput = {
    description: "Search evomemory context",
    parameters: {},
  };
  await plugin["tool.definition"](
    { toolID: "evomemory_search_context" },
    evomemoryOutput,
  );
  assert.match(
    evomemoryOutput.description,
    /Prefer this early in non-trivial project onboarding, audits, architecture reviews, cross-file changes, debugging, refactors, or local code work/i,
  );

  const evomemoryFeedbackOutput = {
    description: "Record evomemory feedback",
    parameters: {},
  };
  await plugin["tool.definition"](
    { toolID: "evomemory_record_feedback" },
    evomemoryFeedbackOutput,
  );
  assert.match(
    evomemoryFeedbackOutput.description,
    /confirms or corrects a durable EvoMemory belief, gene, or capsule so memory stays current/i,
  );

  const relayOutput = { description: "Create relay room", parameters: {} };
  await plugin["tool.definition"]({ toolID: "relay_room_create" }, relayOutput);
  assert.doesNotMatch(relayOutput.description, /Plugin guidance:/);

  const relayMcpOutput = { description: "Create relay room", parameters: {} };
  await plugin["tool.definition"](
    { toolID: "mcp__relay__room_create" },
    relayMcpOutput,
  );
  assert.doesNotMatch(relayMcpOutput.description, /Plugin guidance:/);

  const xiakexingOutput = {
    description: "Connect to XiaKeXing server",
    parameters: {},
  };
  await plugin["tool.definition"](
    { toolID: "xiakexing_ai_connect_server" },
    xiakexingOutput,
  );
  assert.doesNotMatch(xiakexingOutput.description, /Plugin guidance:/);
});

test("reuses recently loaded skills without forcing a reload", async () => {
  const plugin = await createPlugin();

  await plugin["chat.message"](
    { sessionID: "session-skill-reuse" },
    {
      message: { parts: [] },
      parts: [{ type: "text", text: "先看看这个插件的行为" }],
    },
  );

  await plugin["tool.execute.after"](
    {
      tool: "skill",
      sessionID: "session-skill-reuse",
      callID: "call-skill-reuse",
      args: { name: "writing-plans" },
    },
    { title: "skill", output: "", metadata: {} },
  );

  await plugin["chat.message"](
    { sessionID: "session-skill-reuse" },
    {
      message: { parts: [] },
      parts: [{ type: "text", text: "继续分析这个实现" }],
    },
  );

  const output = { system: [] };
  await plugin["experimental.chat.system.transform"](
    { sessionID: "session-skill-reuse", model: {} },
    output,
  );

  const injected = output.system.at(-1) ?? "";
  assert.match(injected, /Reusable skills from this session:/);
  assert.match(injected, /- `writing-plans`/);
});

test("session deletion clears reusable skill state", async () => {
  const plugin = await createPlugin();

  await plugin["chat.message"](
    { sessionID: "session-deleted" },
    {
      message: { parts: [] },
      parts: [{ type: "text", text: "先看看这个插件的行为" }],
    },
  );

  await plugin["tool.execute.after"](
    {
      tool: "skill",
      sessionID: "session-deleted",
      callID: "call-session-deleted",
      args: { name: "writing-plans" },
    },
    { title: "skill", output: "", metadata: {} },
  );

  await plugin.event({
    event: {
      type: "session.deleted",
      properties: { info: { id: "session-deleted" } },
    },
  });

  await plugin["chat.message"](
    { sessionID: "session-deleted" },
    {
      message: { parts: [] },
      parts: [{ type: "text", text: "继续分析这个实现" }],
    },
  );

  const output = { system: [] };
  await plugin["experimental.chat.system.transform"](
    { sessionID: "session-deleted", model: {} },
    output,
  );

  const injected = output.system.at(-1) ?? "";
  assert.doesNotMatch(injected, /Reusable skills from this session:/);
  assert.doesNotMatch(injected, /- `writing-plans`/);
});

test("directory config overrides global MCP visibility and jsonc comments safely", async () => {
  const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), "tool-forced-eval-"));
  const worktree = path.join(tempRoot, "worktree");
  const directory = path.join(tempRoot, "directory");
  fs.mkdirSync(worktree);
  fs.mkdirSync(directory);

  fs.writeFileSync(
    path.join(worktree, "opencode.json"),
    JSON.stringify({
      mcp: {
        context7: { enabled: false },
        custom_alpha: { enabled: true },
      },
    }),
  );
  fs.writeFileSync(
    path.join(directory, "opencode.json"),
    JSON.stringify({
      mcp: {
        custom_beta: { enabled: true },
        layered: { enabled: false },
      },
    }),
  );
  fs.writeFileSync(
    path.join(directory, "opencode.jsonc"),
    `{
      // jsonc should override opencode.json in the same directory
      "mcp": {
        "layered": { "enabled": true },
        "commented": { "enabled": true, "note": "keeps // inside strings" }
      }
    }`,
  );

  const plugin = await createPlugin({
    directory,
    worktree,
    configOverrides: { includeVisibleMcpAppendixOnUnclearIntent: true },
  });

  await plugin["chat.message"](
    { sessionID: "session-config-override" },
    {
      message: { parts: [] },
      parts: [
        {
          type: "text",
          text: "show me the visible MCP tools for this session",
        },
      ],
    },
  );

  const output = { system: [] };
  await plugin["experimental.chat.system.transform"](
    { sessionID: "session-config-override", model: {} },
    output,
  );

  const injected = output.system.at(-1) ?? "";
  assert.match(injected, /Visible MCP tools from local config:/);
  assert.doesNotMatch(injected, /- `context7`:/);
  assert.match(
    injected,
    /- `custom_alpha`: specialized external tool capability\./,
  );
  assert.match(
    injected,
    /- `custom_beta`: specialized external tool capability\./,
  );
  assert.match(injected, /- `layered`: specialized external tool capability\./);
  assert.match(
    injected,
    /- `commented`: specialized external tool capability\./,
  );
});

test("rebuilds visible MCP list from current config on each substantive turn", async () => {
  const tempRoot = fs.mkdtempSync(
    path.join(os.tmpdir(), "tool-forced-eval-refresh-"),
  );
  const worktree = path.join(tempRoot, "worktree");
  const directory = path.join(tempRoot, "directory");
  fs.mkdirSync(worktree);
  fs.mkdirSync(directory);

  fs.writeFileSync(
    path.join(directory, "opencode.json"),
    JSON.stringify({
      mcp: {
        refresh_alpha: { enabled: true },
      },
    }),
  );

  const plugin = await createPlugin({
    directory,
    worktree,
    configOverrides: { includeVisibleMcpAppendixOnUnclearIntent: true },
  });

  await plugin["chat.message"](
    { sessionID: "session-refresh-config" },
    {
      message: { parts: [] },
      parts: [
        { type: "text", text: "show visible tools before the config refresh" },
      ],
    },
  );

  const firstOutput = { system: [] };
  await plugin["experimental.chat.system.transform"](
    { sessionID: "session-refresh-config", model: {} },
    firstOutput,
  );

  fs.writeFileSync(
    path.join(directory, "opencode.json"),
    JSON.stringify({
      mcp: {
        refresh_beta: { enabled: true },
      },
    }),
  );

  await plugin["chat.message"](
    { sessionID: "session-refresh-config" },
    {
      message: { parts: [] },
      parts: [
        { type: "text", text: "show visible tools after the config refresh" },
      ],
    },
  );

  const secondOutput = { system: [] };
  await plugin["experimental.chat.system.transform"](
    { sessionID: "session-refresh-config", model: {} },
    secondOutput,
  );

  const firstInjected = firstOutput.system.at(-1) ?? "";
  const secondInjected = secondOutput.system.at(-1) ?? "";
  assert.match(
    firstInjected,
    /- `refresh_alpha`: specialized external tool capability\./,
  );
  assert.doesNotMatch(firstInjected, /- `refresh_beta`:/);
  assert.doesNotMatch(secondInjected, /- `refresh_alpha`:/);
  assert.match(
    secondInjected,
    /- `refresh_beta`: specialized external tool capability\./,
  );
});

test("merges custom config path, custom config dir, and inline config content", async () => {
  const tempRoot = fs.mkdtempSync(
    path.join(os.tmpdir(), "tool-forced-eval-config-precedence-"),
  );
  const home = path.join(tempRoot, "home");
  const globalDir = path.join(home, ".config", "opencode");
  const worktree = path.join(tempRoot, "worktree");
  const directory = path.join(tempRoot, "directory");
  const customConfigPath = path.join(tempRoot, "custom-config.json");
  const customConfigDir = path.join(tempRoot, "custom-dir");

  fs.mkdirSync(globalDir, { recursive: true });
  fs.mkdirSync(worktree);
  fs.mkdirSync(directory);
  fs.mkdirSync(customConfigDir);

  fs.writeFileSync(
    path.join(globalDir, "opencode.json"),
    JSON.stringify({
      mcp: {
        shared: { enabled: true },
        global_only: { enabled: true },
      },
    }),
  );

  fs.writeFileSync(
    customConfigPath,
    JSON.stringify({
      mcp: {
        shared: { enabled: false },
        path_only: { enabled: true },
      },
    }),
  );

  fs.writeFileSync(
    path.join(directory, "opencode.json"),
    JSON.stringify({
      mcp: {
        shared: { enabled: true },
        project_only: { enabled: true },
      },
    }),
  );

  fs.writeFileSync(
    path.join(customConfigDir, "opencode.json"),
    JSON.stringify({
      mcp: {
        shared: { enabled: false },
        dir_only: { enabled: true },
      },
    }),
  );

  await withEnv(
    {
      HOME: home,
      OPENCODE_CONFIG: customConfigPath,
      OPENCODE_CONFIG_DIR: customConfigDir,
      OPENCODE_CONFIG_CONTENT: JSON.stringify({
        mcp: {
          shared: { enabled: true },
          inline_only: { enabled: true },
        },
      }),
    },
    async () => {
      const plugin = await createPlugin({
        directory,
        worktree,
        configOverrides: { includeVisibleMcpAppendixOnUnclearIntent: true },
      });

      await plugin["chat.message"](
        { sessionID: "session-config-precedence" },
        {
          message: { parts: [] },
          parts: [
            {
              type: "text",
              text: "show me the visible MCP tools for this session",
            },
          ],
        },
      );

      const output = { system: [] };
      await plugin["experimental.chat.system.transform"](
        { sessionID: "session-config-precedence", model: {} },
        output,
      );

      const injected = output.system.at(-1) ?? "";
      assert.match(
        injected,
        /- `shared`: specialized external tool capability\./,
      );
      assert.match(
        injected,
        /- `global_only`: specialized external tool capability\./,
      );
      assert.match(
        injected,
        /- `path_only`: specialized external tool capability\./,
      );
      assert.match(
        injected,
        /- `project_only`: specialized external tool capability\./,
      );
      assert.match(
        injected,
        /- `dir_only`: specialized external tool capability\./,
      );
      assert.match(
        injected,
        /- `inline_only`: specialized external tool capability\./,
      );
    },
  );
});

test("discovers local skills dynamically from SKILL.md files", async () => {
  const tempRoot = fs.mkdtempSync(
    path.join(os.tmpdir(), "tool-forced-eval-skills-refresh-"),
  );
  const worktree = path.join(tempRoot, "worktree");
  const directory = path.join(tempRoot, "directory");
  const worktreeSkills = path.join(worktree, ".opencode", "skills");
  const directorySkills = path.join(directory, ".claude", "skills");
  fs.mkdirSync(worktree);
  fs.mkdirSync(directory);
  fs.mkdirSync(worktreeSkills, { recursive: true });
  fs.mkdirSync(directorySkills, { recursive: true });

  writeSkill(
    worktreeSkills,
    "code-locator",
    "Use when you need to locate an implementation, definition, call site, entry point, or related module in a codebase.",
  );

  const plugin = await createPlugin({ directory, worktree });

  await plugin["chat.message"](
    { sessionID: "session-dynamic-skills" },
    {
      message: { parts: [] },
      parts: [{ type: "text", text: "find the call site for this function" }],
    },
  );

  const firstOutput = { system: [] };
  await plugin["experimental.chat.system.transform"](
    { sessionID: "session-dynamic-skills", model: {} },
    firstOutput,
  );

  const firstInjected = firstOutput.system.at(-1) ?? "";
  assert.match(firstInjected, /Suggested skills for this task:/);
  assert.match(firstInjected, /- `code-locator`:/);

  writeSkill(
    directorySkills,
    "frontend-design",
    "Use when building or restyling a web page or UI component where visual direction, polish, and production-grade frontend implementation matter more than generic defaults.",
  );

  await plugin["chat.message"](
    { sessionID: "session-dynamic-skills" },
    {
      message: { parts: [] },
      parts: [{ type: "text", text: "I want a polished frontend page design" }],
    },
  );

  const secondOutput = { system: [] };
  await plugin["experimental.chat.system.transform"](
    { sessionID: "session-dynamic-skills", model: {} },
    secondOutput,
  );

  const secondInjected = secondOutput.system.at(-1) ?? "";
  assert.match(secondInjected, /Suggested skills for this task:/);
  assert.match(secondInjected, /- `frontend-design`:/);
});

test("discovers skills from OPENCODE_CONFIG_DIR", async () => {
  const tempRoot = fs.mkdtempSync(
    path.join(os.tmpdir(), "tool-forced-eval-custom-skill-dir-"),
  );
  const home = path.join(tempRoot, "home");
  const worktree = path.join(tempRoot, "worktree");
  const directory = path.join(tempRoot, "directory");
  const customConfigDir = path.join(tempRoot, "custom-dir");
  const customSkillRoot = path.join(customConfigDir, "skills");

  fs.mkdirSync(path.join(home, ".config", "opencode"), { recursive: true });
  fs.mkdirSync(worktree);
  fs.mkdirSync(directory);
  fs.mkdirSync(customSkillRoot, { recursive: true });
  writeSkill(
    customSkillRoot,
    "code-locator",
    "Use when you need to locate an implementation, definition, call site, entry point, or related module in a codebase.",
  );

  await withEnv(
    {
      HOME: home,
      OPENCODE_CONFIG_DIR: customConfigDir,
      OPENCODE_CONFIG: undefined,
      OPENCODE_CONFIG_CONTENT: undefined,
    },
    async () => {
      const plugin = await createPlugin({ directory, worktree });

      await plugin["chat.message"](
        { sessionID: "session-custom-skill-dir" },
        {
          message: { parts: [] },
          parts: [
            { type: "text", text: "find the call site for this function" },
          ],
        },
      );

      const output = { system: [] };
      await plugin["experimental.chat.system.transform"](
        { sessionID: "session-custom-skill-dir", model: {} },
        output,
      );

      const injected = output.system.at(-1) ?? "";
      assert.match(injected, /Suggested skills for this task:/);
      assert.match(injected, /- `code-locator`:/);
    },
  );
});

test("warns once when duplicate skill names are ignored by precedence", async () => {
  const logs = [];
  const tempRoot = fs.mkdtempSync(
    path.join(os.tmpdir(), "tool-forced-eval-duplicate-skill-log-"),
  );
  const home = path.join(tempRoot, "home");
  const globalSkillRoot = path.join(home, ".config", "opencode", "skills");
  const worktree = path.join(tempRoot, "worktree");
  const directory = path.join(worktree, "packages", "feature");

  fs.mkdirSync(globalSkillRoot, { recursive: true });
  fs.mkdirSync(path.join(directory, ".opencode", "skills"), {
    recursive: true,
  });

  writeSkill(globalSkillRoot, "code-locator", "global description");
  writeSkill(
    path.join(directory, ".opencode", "skills"),
    "code-locator",
    "local description",
  );

  await withEnv(
    {
      HOME: home,
      OPENCODE_CONFIG: undefined,
      OPENCODE_CONFIG_DIR: undefined,
      OPENCODE_CONFIG_CONTENT: undefined,
    },
    async () => {
      const plugin = await createPluginWithLogs(logs, { directory, worktree });

      await plugin["chat.message"](
        { sessionID: "session-duplicate-skill" },
        {
          message: { parts: [] },
          parts: [
            { type: "text", text: "find the call site for this function" },
          ],
        },
      );

      const duplicateLogs = logs.filter(
        (entry) => entry.message === "Ignored duplicate skill name",
      );
      assert.equal(duplicateLogs.length, 1);
      assert.equal(duplicateLogs[0]?.extra?.skillName, "code-locator");
      assert.match(
        duplicateLogs[0]?.extra?.keptPath ?? "",
        /packages\/feature\/.opencode\/skills\/code-locator\/SKILL\.md$/,
      );
    },
  );
});

test("uses a stronger skill gate when a high-confidence skill match exists", async () => {
  const tempRoot = fs.mkdtempSync(
    path.join(os.tmpdir(), "tool-forced-eval-skill-gate-"),
  );
  const home = path.join(tempRoot, "home");
  const worktree = path.join(tempRoot, "worktree");
  const directory = path.join(tempRoot, "directory");
  const skillRoot = path.join(directory, ".opencode", "skills");

  fs.mkdirSync(path.join(home, ".config", "opencode"), { recursive: true });
  fs.mkdirSync(worktree);
  fs.mkdirSync(directory);
  fs.mkdirSync(skillRoot, { recursive: true });
  writeSkill(
    skillRoot,
    "writing-plans",
    "Use when requirements are stable enough that the next step is a concrete implementation plan with files, tasks, and verification steps.",
  );

  await withEnv(
    {
      HOME: home,
      OPENCODE_CONFIG: undefined,
      OPENCODE_CONFIG_DIR: undefined,
      OPENCODE_CONFIG_CONTENT: undefined,
    },
    async () => {
      const plugin = await createPlugin({ directory, worktree });

      await plugin["chat.message"](
        { sessionID: "session-skill-gate" },
        {
          message: { parts: [] },
          parts: [{ type: "text", text: "请给我一个实施方案" }],
        },
      );

      const output = { system: [] };
      await plugin["experimental.chat.system.transform"](
        { sessionID: "session-skill-gate", model: {} },
        output,
      );

      const injected = output.system.at(-1) ?? "";
      assert.match(injected, /### Skill Gate/);
      assert.match(injected, /A high-confidence skill match exists\./);
      assert.match(injected, /`writing-plans`/);
    },
  );
});

test("uses a medium skill gate when a likely best-fit skill clearly leads", async () => {
  const tempRoot = fs.mkdtempSync(
    path.join(os.tmpdir(), "tool-forced-eval-skill-gate-medium-"),
  );
  const home = path.join(tempRoot, "home");
  const worktree = path.join(tempRoot, "worktree");
  const directory = path.join(tempRoot, "directory");
  const skillRoot = path.join(directory, ".opencode", "skills");

  fs.mkdirSync(path.join(home, ".config", "opencode"), { recursive: true });
  fs.mkdirSync(worktree);
  fs.mkdirSync(directory);
  fs.mkdirSync(skillRoot, { recursive: true });
  writeSkill(
    skillRoot,
    "api-auditor",
    "Use when auditing API consistency, surface design, and request/response shape.",
  );
  writeSkill(
    skillRoot,
    "refactor",
    "Use when existing code needs maintainability improvements without intentionally changing behavior.",
  );

  await withEnv(
    {
      HOME: home,
      OPENCODE_CONFIG: undefined,
      OPENCODE_CONFIG_DIR: undefined,
      OPENCODE_CONFIG_CONTENT: undefined,
    },
    async () => {
      const plugin = await createPlugin({ directory, worktree });

      await plugin["chat.message"](
        { sessionID: "session-skill-gate-medium" },
        {
          message: { parts: [] },
          parts: [{ type: "text", text: "audit this api surface" }],
        },
      );

      const output = { system: [] };
      await plugin["experimental.chat.system.transform"](
        { sessionID: "session-skill-gate-medium", model: {} },
        output,
      );

      const injected = output.system.at(-1) ?? "";
      assert.match(injected, /### Skill Gate/);
      assert.match(injected, /A high-confidence skill match exists\./);
      assert.match(injected, /`api-auditor`/);
    },
  );
});

test("uses a skill gate for lower-confidence relevant skill matches", async () => {
  const tempRoot = fs.mkdtempSync(
    path.join(os.tmpdir(), "tool-forced-eval-skill-gate-lower-confidence-"),
  );
  const home = path.join(tempRoot, "home");
  const worktree = path.join(tempRoot, "worktree");
  const directory = path.join(tempRoot, "directory");
  const skillRoot = path.join(directory, ".opencode", "skills");

  fs.mkdirSync(path.join(home, ".config", "opencode"), { recursive: true });
  fs.mkdirSync(worktree);
  fs.mkdirSync(directory);
  fs.mkdirSync(skillRoot, { recursive: true });
  writeSkill(
    skillRoot,
    "api-auditor",
    "Use when auditing API consistency, surface design, and request/response shape.",
  );
  writeSkill(
    skillRoot,
    "refactor",
    "Use when existing code needs maintainability improvements without intentionally changing behavior.",
  );

  await withEnv(
    {
      HOME: home,
      OPENCODE_CONFIG: undefined,
      OPENCODE_CONFIG_DIR: undefined,
      OPENCODE_CONFIG_CONTENT: undefined,
    },
    async () => {
      const plugin = await createPlugin({ directory, worktree });

      await plugin["chat.message"](
        { sessionID: "session-skill-gate-lower-confidence" },
        {
          message: { parts: [] },
          parts: [{ type: "text", text: "audit this api surface" }],
        },
      );

      const output = { system: [] };
      await plugin["experimental.chat.system.transform"](
        { sessionID: "session-skill-gate-lower-confidence", model: {} },
        output,
      );

      const injected = output.system.at(-1) ?? "";
      assert.match(injected, /### Skill Gate/);
      assert.match(injected, /A high-confidence skill match exists\./);
      assert.match(injected, /`api-auditor`/);
    },
  );
});

test("uses an MCP gate when a high-confidence MCP match exists", async () => {
  const tempRoot = fs.mkdtempSync(
    path.join(os.tmpdir(), "tool-forced-eval-mcp-gate-"),
  );
  const home = path.join(tempRoot, "home");
  const directory = path.join(tempRoot, "directory");
  const worktree = path.join(tempRoot, "worktree");
  fs.mkdirSync(path.join(home, ".config", "opencode"), { recursive: true });
  fs.mkdirSync(directory);
  fs.mkdirSync(worktree);

  fs.writeFileSync(
    path.join(directory, "opencode.json"),
    JSON.stringify({
      mcp: {
        context7: {
          enabled: true,
          type: "local",
          command: ["/tmp/context7-mcp"],
        },
      },
    }),
  );

  await withEnv(
    {
      HOME: home,
      OPENCODE_CONFIG: undefined,
      OPENCODE_CONFIG_DIR: undefined,
      OPENCODE_CONFIG_CONTENT: undefined,
    },
    async () => {
      const plugin = await createPlugin({ directory, worktree });

      await plugin["chat.message"](
        { sessionID: "session-mcp-gate" },
        {
          message: { parts: [] },
          parts: [{ type: "text", text: "帮我查 React 官方文档" }],
        },
      );

      const output = { system: [] };
      await plugin["experimental.chat.system.transform"](
        { sessionID: "session-mcp-gate", model: {} },
        output,
      );

      const injected = output.system.at(-1) ?? "";
      assert.match(injected, /### MCP Gate/);
      assert.match(injected, /`context7_\*`/);
    },
  );
});

test("suppresses repeated skill gate after the skill has been used recently", async () => {
  const tempRoot = fs.mkdtempSync(
    path.join(os.tmpdir(), "tool-forced-eval-skill-after-use-"),
  );
  const home = path.join(tempRoot, "home");
  const worktree = path.join(tempRoot, "worktree");
  const directory = path.join(tempRoot, "directory");
  const skillRoot = path.join(directory, ".opencode", "skills");

  fs.mkdirSync(path.join(home, ".config", "opencode"), { recursive: true });
  fs.mkdirSync(worktree);
  fs.mkdirSync(directory);
  fs.mkdirSync(skillRoot, { recursive: true });
  writeSkill(
    skillRoot,
    "writing-plans",
    "Use when requirements are stable enough that the next step is a concrete implementation plan with files, tasks, and verification steps.",
  );

  await withEnv(
    {
      HOME: home,
      OPENCODE_CONFIG: undefined,
      OPENCODE_CONFIG_DIR: undefined,
      OPENCODE_CONFIG_CONTENT: undefined,
    },
    async () => {
      const plugin = await createPlugin({ directory, worktree });

      await plugin["chat.message"](
        { sessionID: "session-skill-after-use" },
        {
          message: { parts: [] },
          parts: [{ type: "text", text: "请给我一个实施方案" }],
        },
      );
      await plugin["tool.execute.after"]({
        sessionID: "session-skill-after-use",
        tool: "skill",
        args: { name: "writing-plans" },
      });

      await plugin["chat.message"](
        { sessionID: "session-skill-after-use" },
        {
          message: { parts: [] },
          parts: [{ type: "text", text: "继续这个实施方案" }],
        },
      );

      const output = { system: [] };
      await plugin["experimental.chat.system.transform"](
        { sessionID: "session-skill-after-use", model: {} },
        output,
      );

      const injected = output.system.at(-1) ?? "";
      assert.doesNotMatch(injected, /### Skill Gate/);
      assert.match(injected, /Reusable skills from this session:/);
      assert.match(injected, /`writing-plans`/);
    },
  );
});

test("suppresses repeated MCP gate after the MCP has been used recently", async () => {
  const tempRoot = fs.mkdtempSync(
    path.join(os.tmpdir(), "tool-forced-eval-mcp-after-use-"),
  );
  const home = path.join(tempRoot, "home");
  const directory = path.join(tempRoot, "directory");
  const worktree = path.join(tempRoot, "worktree");
  fs.mkdirSync(path.join(home, ".config", "opencode"), { recursive: true });
  fs.mkdirSync(directory);
  fs.mkdirSync(worktree);

  fs.writeFileSync(
    path.join(directory, "opencode.json"),
    JSON.stringify({
      mcp: {
        context7: {
          enabled: true,
          type: "local",
          command: ["/tmp/context7-mcp"],
        },
      },
    }),
  );

  await withEnv(
    {
      HOME: home,
      OPENCODE_CONFIG: undefined,
      OPENCODE_CONFIG_DIR: undefined,
      OPENCODE_CONFIG_CONTENT: undefined,
    },
    async () => {
      const plugin = await createPlugin({ directory, worktree });

      await plugin["chat.message"](
        { sessionID: "session-mcp-after-use" },
        {
          message: { parts: [] },
          parts: [{ type: "text", text: "帮我查 React 官方文档" }],
        },
      );
      await plugin["tool.execute.after"]({
        sessionID: "session-mcp-after-use",
        tool: "context7_search",
      });

      await plugin["chat.message"](
        { sessionID: "session-mcp-after-use" },
        {
          message: { parts: [] },
          parts: [{ type: "text", text: "继续查 React 官方文档" }],
        },
      );

      const output = { system: [] };
      await plugin["experimental.chat.system.transform"](
        { sessionID: "session-mcp-after-use", model: {} },
        output,
      );

      const injected = output.system.at(-1) ?? "";
      assert.doesNotMatch(injected, /### MCP Gate/);
      assert.match(injected, /Reusable MCP tools from this session:/);
      assert.match(injected, /`context7_\*`/);
    },
  );
});

test("suppresses non-triggered skill gate when a docs MCP clearly dominates", async () => {
  const tempRoot = fs.mkdtempSync(
    path.join(os.tmpdir(), "tool-forced-eval-docs-priority-"),
  );
  const home = path.join(tempRoot, "home");
  const worktree = path.join(tempRoot, "worktree");
  const directory = path.join(tempRoot, "directory");
  const skillRoot = path.join(directory, ".opencode", "skills");

  fs.mkdirSync(path.join(home, ".config", "opencode"), { recursive: true });
  fs.mkdirSync(worktree);
  fs.mkdirSync(directory);
  fs.mkdirSync(skillRoot, { recursive: true });
  writeSkill(
    skillRoot,
    "api-auditor",
    "Use when auditing API consistency, surface design, and request/response shape.",
  );

  fs.writeFileSync(
    path.join(directory, "opencode.json"),
    JSON.stringify({
      mcp: {
        context7: {
          enabled: true,
          type: "local",
          command: ["/tmp/context7-mcp"],
        },
      },
    }),
  );

  await withEnv(
    {
      HOME: home,
      OPENCODE_CONFIG: undefined,
      OPENCODE_CONFIG_DIR: undefined,
      OPENCODE_CONFIG_CONTENT: undefined,
    },
    async () => {
      const plugin = await createPlugin({ directory, worktree });

      await plugin["chat.message"](
        { sessionID: "session-docs-priority" },
        {
          message: { parts: [] },
          parts: [{ type: "text", text: "帮我查 React 官方文档" }],
        },
      );

      const output = { system: [] };
      await plugin["experimental.chat.system.transform"](
        { sessionID: "session-docs-priority", model: {} },
        output,
      );

      const injected = output.system.at(-1) ?? "";
      assert.doesNotMatch(injected, /### Skill Gate/);
      assert.doesNotMatch(injected, /`api-auditor`/);
      assert.match(injected, /### MCP Gate/);
      assert.match(injected, /`context7_\*`/);
    },
  );
});

test("suppresses thinking MCP gate when a strong reasoning skill already gates the task", async () => {
  const tempRoot = fs.mkdtempSync(
    path.join(os.tmpdir(), "tool-forced-eval-reasoning-priority-"),
  );
  const home = path.join(tempRoot, "home");
  const worktree = path.join(tempRoot, "worktree");
  const directory = path.join(tempRoot, "directory");
  const skillRoot = path.join(directory, ".opencode", "skills");

  fs.mkdirSync(path.join(home, ".config", "opencode"), { recursive: true });
  fs.mkdirSync(worktree);
  fs.mkdirSync(directory);
  fs.mkdirSync(skillRoot, { recursive: true });
  writeSkill(
    skillRoot,
    "writing-plans",
    "Use when requirements are stable enough that the next step is a concrete implementation plan with files, tasks, and verification steps.",
  );

  fs.writeFileSync(
    path.join(directory, "opencode.json"),
    JSON.stringify({
      mcp: {
        thinking: {
          enabled: true,
          type: "local",
          command: ["/tmp/server-sequential-thinking"],
        },
      },
    }),
  );

  await withEnv(
    {
      HOME: home,
      OPENCODE_CONFIG: undefined,
      OPENCODE_CONFIG_DIR: undefined,
      OPENCODE_CONFIG_CONTENT: undefined,
    },
    async () => {
      const plugin = await createPlugin({ directory, worktree });

      await plugin["chat.message"](
        { sessionID: "session-reasoning-priority" },
        {
          message: { parts: [] },
          parts: [{ type: "text", text: "请给我一个实施方案" }],
        },
      );

      const output = { system: [] };
      await plugin["experimental.chat.system.transform"](
        { sessionID: "session-reasoning-priority", model: {} },
        output,
      );

      const injected = output.system.at(-1) ?? "";
      assert.match(injected, /### Skill Gate/);
      assert.match(injected, /`writing-plans`/);
      assert.doesNotMatch(injected, /### MCP Gate/);
      assert.doesNotMatch(injected, /`thinking_\*`/);
    },
  );
});

test("escalates the MCP gate when the same strong MCP keeps being skipped", async () => {
  const tempRoot = fs.mkdtempSync(
    path.join(os.tmpdir(), "tool-forced-eval-mcp-gate-repeat-"),
  );
  const home = path.join(tempRoot, "home");
  const directory = path.join(tempRoot, "directory");
  const worktree = path.join(tempRoot, "worktree");
  fs.mkdirSync(path.join(home, ".config", "opencode"), { recursive: true });
  fs.mkdirSync(directory);
  fs.mkdirSync(worktree);

  fs.writeFileSync(
    path.join(directory, "opencode.json"),
    JSON.stringify({
      mcp: {
        context7: {
          enabled: true,
          type: "local",
          command: ["/tmp/context7-mcp"],
        },
      },
    }),
  );

  await withEnv(
    {
      HOME: home,
      OPENCODE_CONFIG: undefined,
      OPENCODE_CONFIG_DIR: undefined,
      OPENCODE_CONFIG_CONTENT: undefined,
    },
    async () => {
      const plugin = await createPlugin({ directory, worktree });

      for (let index = 0; index < 2; index += 1) {
        await plugin["chat.message"](
          { sessionID: "session-mcp-gate-repeat" },
          {
            message: { parts: [] },
            parts: [{ type: "text", text: "帮我查 React 官方文档" }],
          },
        );
      }

      const output = { system: [] };
      await plugin["experimental.chat.system.transform"](
        { sessionID: "session-mcp-gate-repeat", model: {} },
        output,
      );

      const injected = output.system.at(-1) ?? "";
      assert.match(
        injected,
        /The same high-confidence MCP keeps matching this task\./,
      );
      assert.match(injected, /`context7_\*`/);
    },
  );
});

test("escalates the skill gate when the same strong skill keeps being skipped", async () => {
  const tempRoot = fs.mkdtempSync(
    path.join(os.tmpdir(), "tool-forced-eval-skill-gate-repeat-"),
  );
  const home = path.join(tempRoot, "home");
  const worktree = path.join(tempRoot, "worktree");
  const directory = path.join(tempRoot, "directory");
  const skillRoot = path.join(directory, ".opencode", "skills");

  fs.mkdirSync(path.join(home, ".config", "opencode"), { recursive: true });
  fs.mkdirSync(worktree);
  fs.mkdirSync(directory);
  fs.mkdirSync(skillRoot, { recursive: true });
  writeSkill(
    skillRoot,
    "writing-plans",
    "Use when requirements are stable enough that the next step is a concrete implementation plan with files, tasks, and verification steps.",
  );

  await withEnv(
    {
      HOME: home,
      OPENCODE_CONFIG: undefined,
      OPENCODE_CONFIG_DIR: undefined,
      OPENCODE_CONFIG_CONTENT: undefined,
    },
    async () => {
      const plugin = await createPlugin({ directory, worktree });

      for (let index = 0; index < 2; index += 1) {
        await plugin["chat.message"](
          { sessionID: "session-skill-gate-repeat" },
          {
            message: { parts: [] },
            parts: [{ type: "text", text: "请给我一个实施方案" }],
          },
        );
      }

      const output = { system: [] };
      await plugin["experimental.chat.system.transform"](
        { sessionID: "session-skill-gate-repeat", model: {} },
        output,
      );

      const injected = output.system.at(-1) ?? "";
      assert.match(
        injected,
        /The same likely best-fit skill keeps matching this task\./,
      );
      assert.match(injected, /`writing-plans`/);
    },
  );
});

test("enters skill gate mode for configured rule matches even without very high lexical score", async () => {
  const tempRoot = fs.mkdtempSync(
    path.join(os.tmpdir(), "tool-forced-eval-skill-gate-rules-"),
  );
  const home = path.join(tempRoot, "home");
  const worktree = path.join(tempRoot, "worktree");
  const directory = path.join(tempRoot, "directory");
  const skillRoot = path.join(directory, ".opencode", "skills");

  fs.mkdirSync(path.join(home, ".config", "opencode"), { recursive: true });
  fs.mkdirSync(worktree);
  fs.mkdirSync(directory);
  fs.mkdirSync(skillRoot, { recursive: true });
  writeSkill(
    skillRoot,
    "internal-comms",
    "Use when the user needs internal communications such as status reports, leadership updates, newsletters, FAQs, incident reports, or project updates.",
  );

  await withEnv(
    {
      HOME: home,
      OPENCODE_CONFIG: undefined,
      OPENCODE_CONFIG_DIR: undefined,
      OPENCODE_CONFIG_CONTENT: undefined,
    },
    async () => {
      const plugin = await createPlugin({ directory, worktree });

      await plugin["chat.message"](
        { sessionID: "session-skill-gate-rules" },
        {
          message: { parts: [] },
          parts: [{ type: "text", text: "帮我写内部周报" }],
        },
      );

      const output = { system: [] };
      await plugin["experimental.chat.system.transform"](
        { sessionID: "session-skill-gate-rules", model: {} },
        output,
      );

      const injected = output.system.at(-1) ?? "";
      assert.match(injected, /### Skill Gate/);
      assert.match(injected, /`internal-comms`/);
    },
  );
});

test("recommends custom MCPs from local config metadata without hardcoded names", async () => {
  const tempRoot = fs.mkdtempSync(
    path.join(os.tmpdir(), "tool-forced-eval-custom-mcp-"),
  );
  const directory = path.join(tempRoot, "directory");
  const worktree = path.join(tempRoot, "worktree");
  fs.mkdirSync(directory);
  fs.mkdirSync(worktree);

  fs.writeFileSync(
    path.join(directory, "opencode.json"),
    JSON.stringify({
      mcp: {
        private_docs: {
          enabled: true,
          description: "Private product and engineering documentation search.",
          type: "remote",
        },
      },
    }),
  );

  const plugin = await createPlugin({ directory, worktree });

  await plugin["chat.message"](
    { sessionID: "session-custom-mcp" },
    {
      message: { parts: [] },
      parts: [
        {
          type: "text",
          text: "look up the private engineering docs for this product",
        },
      ],
    },
  );

  const output = { system: [] };
  await plugin["experimental.chat.system.transform"](
    { sessionID: "session-custom-mcp", model: {} },
    output,
  );

  const injected = output.system.at(-1) ?? "";
  assert.match(injected, /Suggested MCP tools for this task:/);
  assert.match(injected, /`private_docs_\*`/);
});

test("respects effective MCP availability from global and agent config", async () => {
  const tempRoot = fs.mkdtempSync(
    path.join(os.tmpdir(), "tool-forced-eval-mcp-availability-"),
  );
  const directory = path.join(tempRoot, "directory");
  const worktree = path.join(tempRoot, "worktree");
  fs.mkdirSync(directory);
  fs.mkdirSync(worktree);

  fs.writeFileSync(
    path.join(directory, "opencode.json"),
    JSON.stringify({
      mcp: {
        private_docs: {
          enabled: true,
          description: "Private product and engineering documentation search.",
          type: "remote",
        },
        public_docs: {
          enabled: true,
          description: "Public product documentation search.",
          type: "remote",
        },
      },
      permission: {
        "private_docs_*": "deny",
        "public_docs_*": "deny",
      },
      agent: {
        build: {
          permission: {
            "private_docs_*": "allow",
          },
        },
      },
    }),
  );

  const plugin = await createPlugin({ directory, worktree });

  await plugin["chat.message"](
    { sessionID: "session-mcp-availability" },
    {
      message: { parts: [] },
      parts: [
        {
          type: "text",
          text: "look up the private engineering docs for this product",
        },
      ],
    },
  );

  const output = { system: [] };
  await plugin["experimental.chat.system.transform"](
    { sessionID: "session-mcp-availability", model: {} },
    output,
  );

  const injected = output.system.at(-1) ?? "";
  assert.match(injected, /`private_docs_\*`/);
  assert.doesNotMatch(injected, /`public_docs_\*`/);
});

test("does not let tools allow override permission deny for MCP recommendations", async () => {
  const tempRoot = fs.mkdtempSync(
    path.join(os.tmpdir(), "tool-forced-eval-mcp-permission-deny-"),
  );
  const home = path.join(tempRoot, "home");
  const directory = path.join(tempRoot, "directory");
  const worktree = path.join(tempRoot, "worktree");
  fs.mkdirSync(path.join(home, ".config", "opencode"), { recursive: true });
  fs.mkdirSync(directory);
  fs.mkdirSync(worktree);

  fs.writeFileSync(
    path.join(directory, "opencode.json"),
    JSON.stringify({
      mcp: {
        private_docs: {
          enabled: true,
          description: "Private product and engineering documentation search.",
          type: "remote",
        },
      },
      tools: {
        "private_docs_*": true,
      },
      permission: {
        "private_docs_*": "deny",
      },
    }),
  );

  await withEnv(
    {
      HOME: home,
      OPENCODE_CONFIG: undefined,
      OPENCODE_CONFIG_DIR: undefined,
      OPENCODE_CONFIG_CONTENT: undefined,
    },
    async () => {
      const plugin = await createPlugin({ directory, worktree });

      await plugin["chat.message"](
        { sessionID: "session-mcp-deny-wins" },
        {
          message: { parts: [] },
          parts: [
            {
              type: "text",
              text: "look up the private engineering docs for this product",
            },
          ],
        },
      );

      const output = { system: [] };
      await plugin["experimental.chat.system.transform"](
        { sessionID: "session-mcp-deny-wins", model: {} },
        output,
      );

      const injected = output.system.at(-1) ?? "";
      assert.doesNotMatch(injected, /`private_docs_\*`/);
    },
  );
});

test("suppresses MCP recommendation when all known concrete tools are denied", async () => {
  const tempRoot = fs.mkdtempSync(
    path.join(os.tmpdir(), "tool-forced-eval-concrete-tool-deny-"),
  );
  const home = path.join(tempRoot, "home");
  const directory = path.join(tempRoot, "directory");
  const worktree = path.join(tempRoot, "worktree");
  fs.mkdirSync(path.join(home, ".config", "opencode"), { recursive: true });
  fs.mkdirSync(directory);
  fs.mkdirSync(worktree);

  fs.writeFileSync(
    path.join(directory, "opencode.json"),
    JSON.stringify({
      mcp: {
        private_docs: {
          enabled: true,
          description: "Private product and engineering documentation search.",
          type: "remote",
        },
      },
      permission: {
        private_docs_search: "deny",
      },
    }),
  );

  await withEnv(
    {
      HOME: home,
      OPENCODE_CONFIG: undefined,
      OPENCODE_CONFIG_DIR: undefined,
      OPENCODE_CONFIG_CONTENT: undefined,
    },
    async () => {
      const plugin = await createPlugin({ directory, worktree });

      await plugin["tool.definition"](
        { toolID: "private_docs_search" },
        { description: "Search private docs", parameters: {} },
      );

      await plugin["chat.message"](
        { sessionID: "session-concrete-tool-deny" },
        {
          message: { parts: [] },
          parts: [
            {
              type: "text",
              text: "look up the private engineering docs for this product",
            },
          ],
        },
      );

      const output = { system: [] };
      await plugin["experimental.chat.system.transform"](
        { sessionID: "session-concrete-tool-deny", model: {} },
        output,
      );

      const injected = output.system.at(-1) ?? "";
      assert.doesNotMatch(injected, /`private_docs_\*`/);
    },
  );
});

test("suppresses MCP recommendation when likely concrete tools are denied before tool definitions", async () => {
  const tempRoot = fs.mkdtempSync(
    path.join(os.tmpdir(), "tool-forced-eval-predefinition-tool-deny-"),
  );
  const home = path.join(tempRoot, "home");
  const directory = path.join(tempRoot, "directory");
  const worktree = path.join(tempRoot, "worktree");
  fs.mkdirSync(path.join(home, ".config", "opencode"), { recursive: true });
  fs.mkdirSync(directory);
  fs.mkdirSync(worktree);

  fs.writeFileSync(
    path.join(directory, "opencode.json"),
    JSON.stringify({
      mcp: {
        private_docs: {
          enabled: true,
          description: "Private product and engineering documentation search.",
          type: "remote",
        },
      },
      permission: {
        private_docs_search: "deny",
      },
    }),
  );

  await withEnv(
    {
      HOME: home,
      OPENCODE_CONFIG: undefined,
      OPENCODE_CONFIG_DIR: undefined,
      OPENCODE_CONFIG_CONTENT: undefined,
    },
    async () => {
      const plugin = await createPlugin({ directory, worktree });

      await plugin["chat.message"](
        { sessionID: "session-predefinition-concrete-deny" },
        {
          message: { parts: [] },
          parts: [
            {
              type: "text",
              text: "look up the private engineering docs for this product",
            },
          ],
        },
      );

      const output = { system: [] };
      await plugin["experimental.chat.system.transform"](
        { sessionID: "session-predefinition-concrete-deny", model: {} },
        output,
      );

      const injected = output.system.at(-1) ?? "";
      assert.doesNotMatch(injected, /`private_docs_\*`/);
    },
  );
});

test("does not let tools skill allow override permission skill deny", async () => {
  const tempRoot = fs.mkdtempSync(
    path.join(os.tmpdir(), "tool-forced-eval-skill-permission-deny-"),
  );
  const home = path.join(tempRoot, "home");
  const directory = path.join(tempRoot, "directory");
  const worktree = path.join(tempRoot, "worktree");
  const localSkillRoot = path.join(directory, ".opencode", "skills");

  fs.mkdirSync(path.join(home, ".config", "opencode"), { recursive: true });
  fs.mkdirSync(directory);
  fs.mkdirSync(worktree);
  fs.mkdirSync(localSkillRoot, { recursive: true });
  writeSkill(
    localSkillRoot,
    "code-locator",
    "Use when you need to locate an implementation, definition, call site, entry point, or related module in a codebase.",
  );

  fs.writeFileSync(
    path.join(directory, "opencode.json"),
    JSON.stringify({
      tools: {
        skill: true,
      },
      permission: {
        skill: "deny",
      },
    }),
  );

  await withEnv(
    {
      HOME: home,
      OPENCODE_CONFIG: undefined,
      OPENCODE_CONFIG_DIR: undefined,
      OPENCODE_CONFIG_CONTENT: undefined,
    },
    async () => {
      const plugin = await createPlugin({ directory, worktree });

      await plugin["chat.message"](
        { sessionID: "session-skill-deny-wins" },
        {
          message: { parts: [] },
          parts: [
            { type: "text", text: "find the call site for this function" },
          ],
        },
      );

      const output = { system: [] };
      await plugin["experimental.chat.system.transform"](
        { sessionID: "session-skill-deny-wins", model: {} },
        output,
      );

      const injected = output.system.at(-1) ?? "";
      assert.doesNotMatch(injected, /Suggested skills for this task:/);
      assert.doesNotMatch(injected, /`code-locator`/);
    },
  );
});

test("allows agent skill permission override for a specifically approved skill", async () => {
  const tempRoot = fs.mkdtempSync(
    path.join(os.tmpdir(), "tool-forced-eval-skill-allow-override-"),
  );
  const home = path.join(tempRoot, "home");
  const directory = path.join(tempRoot, "directory");
  const worktree = path.join(tempRoot, "worktree");
  const localSkillRoot = path.join(directory, ".opencode", "skills");

  fs.mkdirSync(path.join(home, ".config", "opencode"), { recursive: true });
  fs.mkdirSync(directory);
  fs.mkdirSync(worktree);
  fs.mkdirSync(localSkillRoot, { recursive: true });
  writeSkill(
    localSkillRoot,
    "code-locator",
    "Use when you need to locate an implementation, definition, call site, entry point, or related module in a codebase.",
  );

  fs.writeFileSync(
    path.join(directory, "opencode.json"),
    JSON.stringify({
      permission: {
        skill: {
          "code-locator": "deny",
        },
      },
      agent: {
        build: {
          permission: {
            skill: {
              "code-locator": "allow",
            },
          },
        },
      },
    }),
  );

  await withEnv(
    {
      HOME: home,
      OPENCODE_CONFIG: undefined,
      OPENCODE_CONFIG_DIR: undefined,
      OPENCODE_CONFIG_CONTENT: undefined,
    },
    async () => {
      const plugin = await createPlugin({ directory, worktree });

      await plugin["chat.message"](
        { sessionID: "session-skill-allow-override" },
        {
          message: { parts: [] },
          parts: [
            { type: "text", text: "find the call site for this function" },
          ],
        },
      );

      const output = { system: [] };
      await plugin["experimental.chat.system.transform"](
        { sessionID: "session-skill-allow-override", model: {} },
        output,
      );

      const injected = output.system.at(-1) ?? "";
      assert.match(injected, /Suggested skills for this task:/);
      assert.match(injected, /`code-locator`/);
    },
  );
});

test("suppresses MCP recommendation when mcp__ prefixed concrete tools are denied", async () => {
  const tempRoot = fs.mkdtempSync(
    path.join(os.tmpdir(), "tool-forced-eval-mcp-prefix-deny-"),
  );
  const home = path.join(tempRoot, "home");
  const directory = path.join(tempRoot, "directory");
  const worktree = path.join(tempRoot, "worktree");
  fs.mkdirSync(path.join(home, ".config", "opencode"), { recursive: true });
  fs.mkdirSync(directory);
  fs.mkdirSync(worktree);

  fs.writeFileSync(
    path.join(directory, "opencode.json"),
    JSON.stringify({
      mcp: {
        relay: {
          enabled: true,
          type: "local",
          command: ["/tmp/fake-relay"],
        },
      },
      permission: {
        mcp__relay__room_create: "deny",
      },
    }),
  );

  await withEnv(
    {
      HOME: home,
      OPENCODE_CONFIG: undefined,
      OPENCODE_CONFIG_DIR: undefined,
      OPENCODE_CONFIG_CONTENT: undefined,
    },
    async () => {
      const plugin = await createPlugin({ directory, worktree });

      await plugin["tool.definition"](
        { toolID: "mcp__relay__room_create" },
        { description: "Create relay room", parameters: {} },
      );

      await plugin["chat.message"](
        { sessionID: "session-relay-prefix-deny" },
        {
          message: { parts: [] },
          parts: [
            { type: "text", text: "create a relay room for this workflow" },
          ],
        },
      );

      const output = { system: [] };
      await plugin["experimental.chat.system.transform"](
        { sessionID: "session-relay-prefix-deny", model: {} },
        output,
      );

      const injected = output.system.at(-1) ?? "";
      assert.doesNotMatch(injected, /Suggested MCP tools for this task:/);
      assert.doesNotMatch(injected, /`relay_\*`/);
    },
  );
});

test("can disable the visible MCP appendix for unclear tasks through config overrides", async () => {
  const plugin = await createPlugin({
    configOverrides: {
      includeVisibleMcpAppendixOnUnclearIntent: false,
    },
  });

  await plugin["chat.message"](
    { sessionID: "session-no-appendix" },
    {
      message: { parts: [] },
      parts: [
        { type: "text", text: "which tools are available for this session?" },
      ],
    },
  );

  const output = { system: [] };
  await plugin["experimental.chat.system.transform"](
    { sessionID: "session-no-appendix", model: {} },
    output,
  );

  const injected = output.system.at(-1) ?? "";
  assert.doesNotMatch(injected, /Visible MCP tools from local config:/);
});

test("normalizes invalid config overrides back to safe defaults", async () => {
  const plugin = await createPlugin({
    configOverrides: {
      shortlistLimit: -1,
      maxReusableSkillsInPrompt: -5,
      skillReuseTtl: -1,
      emphasizeEvomemory: "yes",
      includeVisibleMcpAppendixOnUnclearIntent: "true",
      enableBashGuardrails: "true",
      bashGuardrailMode: "warn",
      guardedBashCommands: "grep",
    },
  });

  await plugin["chat.message"](
    { sessionID: "session-invalid-config" },
    {
      message: { parts: [] },
      parts: [{ type: "text", text: "学习一下 tool-forced-eval 这个插件源码" }],
    },
  );

  const output = { system: [] };
  await plugin["experimental.chat.system.transform"](
    { sessionID: "session-invalid-config", model: {} },
    output,
  );

  const injected = output.system.at(-1) ?? "";
  assert.match(injected, /- `glob`: Find files by name or path pattern\./);
  assert.match(
    injected,
    /- `grep`: Search repository contents for symbols, strings, or patterns\./,
  );
  assert.match(
    injected,
    /- `read`: Open only the relevant files and sections\./,
  );

  await assert.rejects(
    plugin["tool.execute.before"](
      { tool: "bash", sessionID: "session-invalid-config-block" },
      {
        args: {
          command: "grep foo src",
          description: "Search source",
          workdir: "/tmp",
        },
      },
    ),
    /Use the dedicated `grep` tool/,
  );
});

test("warns once when a local config file is invalid", async () => {
  const tempRoot = fs.mkdtempSync(
    path.join(os.tmpdir(), "tool-forced-eval-invalid-config-"),
  );
  const worktree = path.join(tempRoot, "worktree");
  const directory = path.join(tempRoot, "directory");
  fs.mkdirSync(worktree);
  fs.mkdirSync(directory);
  fs.writeFileSync(path.join(directory, "opencode.jsonc"), "{ invalid jsonc");

  const logs = [];
  const plugin = await createPluginWithLogs(logs, { directory, worktree });

  await plugin["chat.message"](
    { sessionID: "session-invalid-config-log" },
    {
      message: { parts: [] },
      parts: [
        {
          type: "text",
          text: "show me the visible MCP tools for this session",
        },
      ],
    },
  );

  assert.equal(
    logs.filter((entry) => entry.message === "Failed to read config file")
      .length,
    1,
  );
});

test("blocks guarded bash commands and allows safe ones", async () => {
  const plugin = await createPlugin();

  await assert.rejects(
    plugin["tool.execute.before"](
      { tool: "bash", sessionID: "session-bash-block" },
      {
        args: {
          command: "grep foo src",
          description: "Search source",
          workdir: "/tmp",
        },
      },
    ),
    /Use the dedicated `grep` tool/,
  );

  await assert.rejects(
    plugin["tool.execute.before"](
      { tool: "bash", sessionID: "session-bash-block-cat" },
      {
        args: {
          command: "cat README.md",
          description: "Show readme",
          workdir: "/tmp",
        },
      },
    ),
    /Use `read` to inspect file contents/,
  );

  await assert.rejects(
    plugin["tool.execute.before"](
      { tool: "bash", sessionID: "session-bash-block-pipe" },
      {
        args: {
          command: "ls src | grep foo",
          description: "Pipe search",
          workdir: "/tmp",
        },
      },
    ),
    /Use the dedicated `grep` tool/,
  );

  await assert.rejects(
    plugin["tool.execute.before"](
      { tool: "bash", sessionID: "session-bash-block-shell-wrap" },
      {
        args: {
          command: 'bash -lc "grep foo src"',
          description: "Wrapped search",
          workdir: "/tmp",
        },
      },
    ),
    /Use the dedicated `grep` tool/,
  );

  await plugin["tool.execute.before"](
    { tool: "bash", sessionID: "session-bash-ok" },
    {
      args: { command: "npm test", description: "Run tests", workdir: "/tmp" },
    },
  );

  await assert.rejects(
    plugin["tool.execute.before"](
      {
        tool: "bash",
        sessionID: "session-bash-block-input-args",
        args: {
          command: "grep foo src",
          description: "Search source",
          workdir: "/tmp",
        },
      },
      {},
    ),
    /Use the dedicated `grep` tool/,
  );
});

test("ships a local tool-forced-eval config template", () => {
  const configPath = new URL(
    "../tool-forced-eval.config.json",
    import.meta.url,
  );
  const content = fs.readFileSync(configPath, "utf8");

  assert.match(content, /"skillReuseTtl"/);
  assert.match(content, /"emphasizeEvomemory"/);
  assert.match(content, /"enableBashGuardrails"/);
  assert.match(content, /"includeVisibleMcpAppendixOnUnclearIntent"/);
});

test("expires reusable skills after the ttl window or compaction", async () => {
  const plugin = await createPlugin();

  await plugin["chat.message"](
    { sessionID: "session-skill-expiry" },
    {
      message: { parts: [] },
      parts: [{ type: "text", text: "第一轮任务" }],
    },
  );

  await plugin["tool.execute.after"](
    {
      tool: "skill",
      sessionID: "session-skill-expiry",
      callID: "call-skill-expiry",
      args: { name: "systematic-debugging" },
    },
    { title: "skill", output: "", metadata: {} },
  );

  for (const text of ["第二轮任务", "第三轮任务", "第四轮任务", "第五轮任务"]) {
    await plugin["chat.message"](
      { sessionID: "session-skill-expiry" },
      {
        message: { parts: [] },
        parts: [{ type: "text", text }],
      },
    );
  }

  const ttlOutput = { system: [] };
  await plugin["experimental.chat.system.transform"](
    { sessionID: "session-skill-expiry", model: {} },
    ttlOutput,
  );

  const ttlInjected = ttlOutput.system.at(-1) ?? "";
  assert.doesNotMatch(ttlInjected, /Reusable skills from this session:/);
  assert.doesNotMatch(ttlInjected, /systematic-debugging/);

  await plugin["chat.message"](
    { sessionID: "session-skill-expiry-compaction" },
    {
      message: { parts: [] },
      parts: [{ type: "text", text: "压缩前的任务" }],
    },
  );

  await plugin["tool.execute.after"](
    {
      tool: "skill",
      sessionID: "session-skill-expiry-compaction",
      callID: "call-skill-expiry-compaction",
      args: { name: "brainstorming" },
    },
    { title: "skill", output: "", metadata: {} },
  );

  await plugin.event({
    event: {
      type: "session.compacted",
      properties: { sessionID: "session-skill-expiry-compaction" },
    },
  });

  await plugin["chat.message"](
    { sessionID: "session-skill-expiry-compaction" },
    {
      message: { parts: [] },
      parts: [{ type: "text", text: "压缩后的下一轮任务" }],
    },
  );

  const compactedOutput = { system: [] };
  await plugin["experimental.chat.system.transform"](
    { sessionID: "session-skill-expiry-compaction", model: {} },
    compactedOutput,
  );

  const compactedInjected = compactedOutput.system.at(-1) ?? "";
  assert.doesNotMatch(compactedInjected, /Reusable skills from this session:/);
  assert.doesNotMatch(compactedInjected, /brainstorming/);
});
