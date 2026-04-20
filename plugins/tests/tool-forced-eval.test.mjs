import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'

import { ToolForcedEvalPlugin } from '../tool-forced-eval.js'

const createPlugin = (options = {}) =>
  ToolForcedEvalPlugin({
    client: { app: { log: async () => {} } },
    directory: options.directory ?? '/home/mechrevo/.config/opencode',
    worktree: options.worktree ?? '/home/mechrevo/.config/opencode',
    configOverrides: options.configOverrides,
  })

const createPluginWithLogs = (logs, options = {}) =>
  ToolForcedEvalPlugin({
    client: { app: { log: async (entry) => logs.push(entry.body) } },
    directory: options.directory ?? '/home/mechrevo/.config/opencode',
    worktree: options.worktree ?? '/home/mechrevo/.config/opencode',
    configOverrides: options.configOverrides,
  })

test('injects routed tool-forced-eval guidance through system transform', async () => {
  const plugin = await createPlugin()

  await plugin['chat.message'](
    { sessionID: 'session-system-prompt' },
    {
      message: { parts: [] },
      parts: [{ type: 'text', text: '学习一下 tool-forced-eval 这个插件源码' }],
    },
  )

  const output = { system: [] }
  await plugin['experimental.chat.system.transform'](
    { sessionID: 'session-system-prompt', model: {} },
    output,
  )

  const injected = output.system.at(-1) ?? ''

  assert.match(injected, /^<OPENCODE_TOOL_FORCED_EVAL>/)
  assert.match(injected, /System workflow reminder for the assistant\./)
  assert.match(injected, /Follow explicit user instructions first\./)
  assert.match(injected, /### Tool Mapping/)
  assert.match(injected, /### Current Task Routing/)
  assert.match(injected, /Detected intent: `local-code`/)
  assert.match(injected, /Inspect the local codebase with native workspace tools before reaching for MCPs\./)
  assert.match(injected, /Preferred native tools right now:/)
  assert.match(injected, /- `glob`: Find files by name or path pattern\./)
  assert.match(injected, /- `grep`: Search repository contents for symbols, strings, or patterns\./)
  assert.match(injected, /- `read`: Open only the relevant files and sections\./)
  assert.match(injected, /### Guardrails/)
  assert.match(injected, /Prefer dedicated workspace tools over `bash` for simple repository search or file-reading work\./)
  assert.doesNotMatch(injected, /### EvoMemory Priority/)
  assert.doesNotMatch(injected, /Visible MCP tools from local config:/)
  assert.doesNotMatch(injected, /must call the skill tool/i)
  assert.doesNotMatch(injected, /call the MCP tool immediately/i)
})

test('skips system prompt injection for slash commands', async () => {
  const plugin = await createPlugin()

  await plugin['chat.message'](
    { sessionID: 'session-slash-command' },
    {
      message: { parts: [] },
      parts: [{ type: 'text', text: '/review' }],
    },
  )

  const output = { system: [] }
  await plugin['experimental.chat.system.transform'](
    { sessionID: 'session-slash-command', model: {} },
    output,
  )

  assert.equal(output.system.length, 0)
})

test('logs why task routing guidance was skipped', async () => {
  const logs = []
  const plugin = await createPluginWithLogs(logs)

  for (const [sessionID, text] of [
    ['session-skip-slash', '/review'],
    ['session-skip-small-talk', 'ok'],
    ['session-skip-marker', 'please do not repeat <OPENCODE_TOOL_FORCED_EVAL>'],
  ]) {
    await plugin['chat.message'](
      { sessionID },
      {
        message: { parts: [] },
        parts: [{ type: 'text', text }],
      },
    )
  }

  const skippedLogs = logs.filter((entry) => entry.message === 'Skipped task routing guidance')
  assert.equal(skippedLogs.length, 3)
  assert.deepEqual(
    skippedLogs.map((entry) => entry.extra?.skipReason).sort(),
    ['marker-echo', 'slash-command', 'small-talk'],
  )
})

test('skips system prompt injection for tiny english and chinese small-talk plus marker echoes', async () => {
  const plugin = await createPlugin()

  await plugin['chat.message'](
    { sessionID: 'session-small-talk-en' },
    {
      message: { parts: [] },
      parts: [{ type: 'text', text: 'ok' }],
    },
  )

  const englishOutput = { system: [] }
  await plugin['experimental.chat.system.transform'](
    { sessionID: 'session-small-talk-en', model: {} },
    englishOutput,
  )
  assert.equal(englishOutput.system.length, 0)

  await plugin['chat.message'](
    { sessionID: 'session-small-talk-zh' },
    {
      message: { parts: [] },
      parts: [{ type: 'text', text: '好的' }],
    },
  )

  const chineseOutput = { system: [] }
  await plugin['experimental.chat.system.transform'](
    { sessionID: 'session-small-talk-zh', model: {} },
    chineseOutput,
  )
  assert.equal(chineseOutput.system.length, 0)

  await plugin['chat.message'](
    { sessionID: 'session-substantive-zh' },
    {
      message: { parts: [] },
      parts: [{ type: 'text', text: '继续分析这个实现' }],
    },
  )

  const substantiveOutput = { system: [] }
  await plugin['experimental.chat.system.transform'](
    { sessionID: 'session-substantive-zh', model: {} },
    substantiveOutput,
  )
  assert.equal(substantiveOutput.system.length, 1)

  await plugin['chat.message'](
    { sessionID: 'session-small-talk-zh' },
    {
      message: { parts: [] },
      parts: [{ type: 'text', text: 'please do not repeat <OPENCODE_TOOL_FORCED_EVAL>' }],
    },
  )

  const markerOutput = { system: [] }
  await plugin['experimental.chat.system.transform'](
    { sessionID: 'session-small-talk-zh', model: {} },
    markerOutput,
  )
  assert.equal(markerOutput.system.length, 0)
})

test('routes history, docs, and GitHub pattern tasks to the right MCP shortlists', async () => {
  const plugin = await createPlugin()

  await plugin['chat.message'](
    { sessionID: 'session-memory-maintenance' },
    {
      message: { parts: [] },
      parts: [{ type: 'text', text: 'use evomemory_record_feedback to correct stale beliefs after this task' }],
    },
  )
  const maintenanceOutput = { system: [] }
  await plugin['experimental.chat.system.transform']({ sessionID: 'session-memory-maintenance', model: {} }, maintenanceOutput)
  const maintenanceInjected = maintenanceOutput.system.at(-1) ?? ''
  assert.match(maintenanceInjected, /### EvoMemory Priority/)
  assert.match(maintenanceInjected, /Detected intent: `memory-maintenance`/)
  assert.match(maintenanceInjected, /Use EvoMemory to inspect existing context and keep durable memory current as the task confirms, corrects, or reconciles prior state\./)
  assert.match(maintenanceInjected, /`evomemory_\*`/)

  await plugin['chat.message'](
    { sessionID: 'session-history' },
    {
      message: { parts: [] },
      parts: [{ type: 'text', text: 'review prior project decisions about tool-forced-eval' }],
    },
  )
  const historyOutput = { system: [] }
  await plugin['experimental.chat.system.transform']({ sessionID: 'session-history', model: {} }, historyOutput)
  const historyInjected = historyOutput.system.at(-1) ?? ''
  assert.match(historyInjected, /### EvoMemory Priority/)
  assert.match(historyInjected, /Detected intent: `history`/)
  assert.match(historyInjected, /Suggested MCP tools for this task:/)
  assert.match(historyInjected, /`evomemory_\*`/)
  assert.doesNotMatch(historyInjected, /`context7_\*`/)

  await plugin['chat.message'](
    { sessionID: 'session-docs' },
    {
      message: { parts: [] },
      parts: [{ type: 'text', text: 'look up the React useEffectEvent docs' }],
    },
  )
  const docsOutput = { system: [] }
  await plugin['experimental.chat.system.transform']({ sessionID: 'session-docs', model: {} }, docsOutput)
  const docsInjected = docsOutput.system.at(-1) ?? ''
  assert.match(docsInjected, /Detected intent: `docs`/)
  assert.match(docsInjected, /`context7_\*`/)

  await plugin['chat.message'](
    { sessionID: 'session-oss' },
    {
      message: { parts: [] },
      parts: [{ type: 'text', text: 'go search similar OpenCode plugins on GitHub' }],
    },
  )
  const ossOutput = { system: [] }
  await plugin['experimental.chat.system.transform']({ sessionID: 'session-oss', model: {} }, ossOutput)
  const ossInjected = ossOutput.system.at(-1) ?? ''
  assert.match(ossInjected, /Detected intent: `oss-patterns`/)
  assert.match(ossInjected, /`grep_app_\*`/)

  await plugin['chat.message'](
    { sessionID: 'session-local-code' },
    {
      message: { parts: [] },
      parts: [{ type: 'text', text: 'please explain the current implementation in plugins/tool-forced-eval.js' }],
    },
  )
  const codeOutput = { system: [] }
  await plugin['experimental.chat.system.transform']({ sessionID: 'session-local-code', model: {} }, codeOutput)
  const codeInjected = codeOutput.system.at(-1) ?? ''
  assert.match(codeInjected, /Detected intent: `local-code`/)
  assert.match(codeInjected, /- `glob`:/)
  assert.doesNotMatch(codeInjected, /`evomemory_\*`/)
})

test('only adds tool guidance for MCPs that still opt in', async () => {
  const plugin = await createPlugin()

  const context7Output = { description: 'Query docs', parameters: {} }
  await plugin['tool.definition']({ toolID: 'context7_query-docs' }, context7Output)
  assert.match(context7Output.description, /Plugin guidance:/)

  const evomemoryOutput = { description: 'Search evomemory context', parameters: {} }
  await plugin['tool.definition']({ toolID: 'evomemory_search_context' }, evomemoryOutput)
  assert.match(
    evomemoryOutput.description,
    /Prefer this early in non-trivial tasks when prior decisions, stable constraints, earlier fixes, or historical feedback may matter/i,
  )

  const evomemoryFeedbackOutput = { description: 'Record evomemory feedback', parameters: {} }
  await plugin['tool.definition']({ toolID: 'evomemory_record_feedback' }, evomemoryFeedbackOutput)
  assert.match(
    evomemoryFeedbackOutput.description,
    /confirms or corrects a durable EvoMemory belief, gene, or capsule so memory stays current/i,
  )

  const relayOutput = { description: 'Create relay room', parameters: {} }
  await plugin['tool.definition']({ toolID: 'relay_room_create' }, relayOutput)
  assert.doesNotMatch(relayOutput.description, /Plugin guidance:/)

  const relayMcpOutput = { description: 'Create relay room', parameters: {} }
  await plugin['tool.definition']({ toolID: 'mcp__relay__room_create' }, relayMcpOutput)
  assert.doesNotMatch(relayMcpOutput.description, /Plugin guidance:/)

  const xiakexingOutput = { description: 'Connect to XiaKeXing server', parameters: {} }
  await plugin['tool.definition']({ toolID: 'xiakexing_ai_connect_server' }, xiakexingOutput)
  assert.doesNotMatch(xiakexingOutput.description, /Plugin guidance:/)
})

test('reuses recently loaded skills without forcing a reload', async () => {
  const plugin = await createPlugin()

  await plugin['chat.message'](
    { sessionID: 'session-skill-reuse' },
    {
      message: { parts: [] },
      parts: [{ type: 'text', text: '先看看这个插件的行为' }],
    },
  )

  await plugin['tool.execute.after'](
    {
      tool: 'skill',
      sessionID: 'session-skill-reuse',
      callID: 'call-skill-reuse',
      args: { name: 'writing-plans' },
    },
    { title: 'skill', output: '', metadata: {} },
  )

  await plugin['chat.message'](
    { sessionID: 'session-skill-reuse' },
    {
      message: { parts: [] },
      parts: [{ type: 'text', text: '继续分析这个实现' }],
    },
  )

  const output = { system: [] }
  await plugin['experimental.chat.system.transform'](
    { sessionID: 'session-skill-reuse', model: {} },
    output,
  )

  const injected = output.system.at(-1) ?? ''
  assert.match(injected, /Reusable skills from this session:/)
  assert.match(injected, /- `writing-plans`/)
})

test('session deletion clears reusable skill state', async () => {
  const plugin = await createPlugin()

  await plugin['chat.message'](
    { sessionID: 'session-deleted' },
    {
      message: { parts: [] },
      parts: [{ type: 'text', text: '先看看这个插件的行为' }],
    },
  )

  await plugin['tool.execute.after'](
    {
      tool: 'skill',
      sessionID: 'session-deleted',
      callID: 'call-session-deleted',
      args: { name: 'writing-plans' },
    },
    { title: 'skill', output: '', metadata: {} },
  )

  await plugin.event({
    event: {
      type: 'session.deleted',
      properties: { info: { id: 'session-deleted' } },
    },
  })

  await plugin['chat.message'](
    { sessionID: 'session-deleted' },
    {
      message: { parts: [] },
      parts: [{ type: 'text', text: '继续分析这个实现' }],
    },
  )

  const output = { system: [] }
  await plugin['experimental.chat.system.transform'](
    { sessionID: 'session-deleted', model: {} },
    output,
  )

  const injected = output.system.at(-1) ?? ''
  assert.doesNotMatch(injected, /Reusable skills from this session:/)
  assert.doesNotMatch(injected, /- `writing-plans`/)
})

test('directory config overrides global MCP visibility and jsonc comments safely', async () => {
  const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'tool-forced-eval-'))
  const worktree = path.join(tempRoot, 'worktree')
  const directory = path.join(tempRoot, 'directory')
  fs.mkdirSync(worktree)
  fs.mkdirSync(directory)

  fs.writeFileSync(
    path.join(worktree, 'opencode.json'),
    JSON.stringify({
      mcp: {
        context7: { enabled: false },
        custom_alpha: { enabled: true },
      },
    }),
  )
  fs.writeFileSync(
    path.join(directory, 'opencode.json'),
    JSON.stringify({
      mcp: {
        custom_beta: { enabled: true },
        layered: { enabled: false },
      },
    }),
  )
  fs.writeFileSync(
    path.join(directory, 'opencode.jsonc'),
    `{
      // jsonc should override opencode.json in the same directory
      "mcp": {
        "layered": { "enabled": true },
        "commented": { "enabled": true, "note": "keeps // inside strings" }
      }
    }`,
  )

  const plugin = await createPlugin({ directory, worktree })

  await plugin['chat.message'](
    { sessionID: 'session-config-override' },
    {
      message: { parts: [] },
      parts: [{ type: 'text', text: 'show me the visible MCP tools for this session' }],
    },
  )

  const output = { system: [] }
  await plugin['experimental.chat.system.transform'](
    { sessionID: 'session-config-override', model: {} },
    output,
  )

  const injected = output.system.at(-1) ?? ''
  assert.match(injected, /Visible MCP tools from local config:/)
  assert.doesNotMatch(injected, /- `context7`:/)
  assert.match(injected, /- `custom_alpha`: specialized external tool capability\./)
  assert.match(injected, /- `custom_beta`: specialized external tool capability\./)
  assert.match(injected, /- `layered`: specialized external tool capability\./)
  assert.match(injected, /- `commented`: specialized external tool capability\./)
})

test('rebuilds visible MCP list from current config on each substantive turn', async () => {
  const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'tool-forced-eval-refresh-'))
  const worktree = path.join(tempRoot, 'worktree')
  const directory = path.join(tempRoot, 'directory')
  fs.mkdirSync(worktree)
  fs.mkdirSync(directory)

  fs.writeFileSync(
    path.join(directory, 'opencode.json'),
    JSON.stringify({
      mcp: {
        refresh_alpha: { enabled: true },
      },
    }),
  )

  const plugin = await createPlugin({ directory, worktree })

  await plugin['chat.message'](
    { sessionID: 'session-refresh-config' },
    {
      message: { parts: [] },
      parts: [{ type: 'text', text: 'show visible tools before the config refresh' }],
    },
  )

  const firstOutput = { system: [] }
  await plugin['experimental.chat.system.transform'](
    { sessionID: 'session-refresh-config', model: {} },
    firstOutput,
  )

  fs.writeFileSync(
    path.join(directory, 'opencode.json'),
    JSON.stringify({
      mcp: {
        refresh_beta: { enabled: true },
      },
    }),
  )

  await plugin['chat.message'](
    { sessionID: 'session-refresh-config' },
    {
      message: { parts: [] },
      parts: [{ type: 'text', text: 'show visible tools after the config refresh' }],
    },
  )

  const secondOutput = { system: [] }
  await plugin['experimental.chat.system.transform'](
    { sessionID: 'session-refresh-config', model: {} },
    secondOutput,
  )

  const firstInjected = firstOutput.system.at(-1) ?? ''
  const secondInjected = secondOutput.system.at(-1) ?? ''
  assert.match(firstInjected, /- `refresh_alpha`: specialized external tool capability\./)
  assert.doesNotMatch(firstInjected, /- `refresh_beta`:/)
  assert.doesNotMatch(secondInjected, /- `refresh_alpha`:/)
  assert.match(secondInjected, /- `refresh_beta`: specialized external tool capability\./)
})

test('can disable the visible MCP appendix for unclear tasks through config overrides', async () => {
  const plugin = await createPlugin({
    configOverrides: {
      includeVisibleMcpAppendixOnUnclearIntent: false,
    },
  })

  await plugin['chat.message'](
    { sessionID: 'session-no-appendix' },
    {
      message: { parts: [] },
      parts: [{ type: 'text', text: 'which tools are available for this session?' }],
    },
  )

  const output = { system: [] }
  await plugin['experimental.chat.system.transform'](
    { sessionID: 'session-no-appendix', model: {} },
    output,
  )

  const injected = output.system.at(-1) ?? ''
  assert.doesNotMatch(injected, /Visible MCP tools from local config:/)
})

test('normalizes invalid config overrides back to safe defaults', async () => {
  const plugin = await createPlugin({
    configOverrides: {
      shortlistLimit: -1,
      maxReusableSkillsInPrompt: -5,
      skillReuseTtl: -1,
      emphasizeEvomemory: 'yes',
      includeVisibleMcpAppendixOnUnclearIntent: 'true',
      enableBashGuardrails: 'true',
      bashGuardrailMode: 'warn',
      guardedBashCommands: 'grep',
    },
  })

  await plugin['chat.message'](
    { sessionID: 'session-invalid-config' },
    {
      message: { parts: [] },
      parts: [{ type: 'text', text: '学习一下 tool-forced-eval 这个插件源码' }],
    },
  )

  const output = { system: [] }
  await plugin['experimental.chat.system.transform'](
    { sessionID: 'session-invalid-config', model: {} },
    output,
  )

  const injected = output.system.at(-1) ?? ''
  assert.match(injected, /- `glob`: Find files by name or path pattern\./)
  assert.match(injected, /- `grep`: Search repository contents for symbols, strings, or patterns\./)
  assert.match(injected, /- `read`: Open only the relevant files and sections\./)

  await assert.rejects(
    plugin['tool.execute.before'](
      { tool: 'bash', sessionID: 'session-invalid-config-block' },
      { args: { command: 'grep foo src', description: 'Search source', workdir: '/tmp' } },
    ),
    /Use the dedicated `grep` tool/,
  )
})

test('warns once when a local config file is invalid', async () => {
  const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'tool-forced-eval-invalid-config-'))
  const worktree = path.join(tempRoot, 'worktree')
  const directory = path.join(tempRoot, 'directory')
  fs.mkdirSync(worktree)
  fs.mkdirSync(directory)
  fs.writeFileSync(path.join(directory, 'opencode.jsonc'), '{ invalid jsonc')

  const logs = []
  const plugin = await createPluginWithLogs(logs, { directory, worktree })

  await plugin['chat.message'](
    { sessionID: 'session-invalid-config-log' },
    {
      message: { parts: [] },
      parts: [{ type: 'text', text: 'show me the visible MCP tools for this session' }],
    },
  )

  assert.equal(
    logs.filter((entry) => entry.message === 'Failed to read config file').length,
    1,
  )
})

test('blocks guarded bash commands and allows safe ones', async () => {
  const plugin = await createPlugin()

  await assert.rejects(
    plugin['tool.execute.before'](
      { tool: 'bash', sessionID: 'session-bash-block' },
      { args: { command: 'grep foo src', description: 'Search source', workdir: '/tmp' } },
    ),
    /Use the dedicated `grep` tool/,
  )

  await assert.rejects(
    plugin['tool.execute.before'](
      { tool: 'bash', sessionID: 'session-bash-block-cat' },
      { args: { command: 'cat README.md', description: 'Show readme', workdir: '/tmp' } },
    ),
    /Use `read` to inspect file contents/,
  )

  await assert.rejects(
    plugin['tool.execute.before'](
      { tool: 'bash', sessionID: 'session-bash-block-pipe' },
      { args: { command: 'ls src | grep foo', description: 'Pipe search', workdir: '/tmp' } },
    ),
    /Use the dedicated `grep` tool/,
  )

  await assert.rejects(
    plugin['tool.execute.before'](
      { tool: 'bash', sessionID: 'session-bash-block-shell-wrap' },
      { args: { command: 'bash -lc "grep foo src"', description: 'Wrapped search', workdir: '/tmp' } },
    ),
    /Use the dedicated `grep` tool/,
  )

  await plugin['tool.execute.before'](
    { tool: 'bash', sessionID: 'session-bash-ok' },
    { args: { command: 'npm test', description: 'Run tests', workdir: '/tmp' } },
  )

  await assert.rejects(
    plugin['tool.execute.before'](
      {
        tool: 'bash',
        sessionID: 'session-bash-block-input-args',
        args: { command: 'grep foo src', description: 'Search source', workdir: '/tmp' },
      },
      {},
    ),
    /Use the dedicated `grep` tool/,
  )
})

test('ships a local tool-forced-eval config template', () => {
  const configPath = new URL('../tool-forced-eval.config.json', import.meta.url)
  const content = fs.readFileSync(configPath, 'utf8')

  assert.match(content, /"skillReuseTtl"/)
  assert.match(content, /"emphasizeEvomemory"/)
  assert.match(content, /"enableBashGuardrails"/)
  assert.match(content, /"includeVisibleMcpAppendixOnUnclearIntent"/)
})

test('expires reusable skills after the ttl window or compaction', async () => {
  const plugin = await createPlugin()

  await plugin['chat.message'](
    { sessionID: 'session-skill-expiry' },
    {
      message: { parts: [] },
      parts: [{ type: 'text', text: '第一轮任务' }],
    },
  )

  await plugin['tool.execute.after'](
    {
      tool: 'skill',
      sessionID: 'session-skill-expiry',
      callID: 'call-skill-expiry',
      args: { name: 'systematic-debugging' },
    },
    { title: 'skill', output: '', metadata: {} },
  )

  for (const text of ['第二轮任务', '第三轮任务', '第四轮任务', '第五轮任务']) {
    await plugin['chat.message'](
      { sessionID: 'session-skill-expiry' },
      {
        message: { parts: [] },
        parts: [{ type: 'text', text }],
      },
    )
  }

  const ttlOutput = { system: [] }
  await plugin['experimental.chat.system.transform'](
    { sessionID: 'session-skill-expiry', model: {} },
    ttlOutput,
  )

  const ttlInjected = ttlOutput.system.at(-1) ?? ''
  assert.doesNotMatch(ttlInjected, /Reusable skills from this session:/)
  assert.doesNotMatch(ttlInjected, /systematic-debugging/)

  await plugin['chat.message'](
    { sessionID: 'session-skill-expiry-compaction' },
    {
      message: { parts: [] },
      parts: [{ type: 'text', text: '压缩前的任务' }],
    },
  )

  await plugin['tool.execute.after'](
    {
      tool: 'skill',
      sessionID: 'session-skill-expiry-compaction',
      callID: 'call-skill-expiry-compaction',
      args: { name: 'brainstorming' },
    },
    { title: 'skill', output: '', metadata: {} },
  )

  await plugin.event({
    event: {
      type: 'session.compacted',
      properties: { sessionID: 'session-skill-expiry-compaction' },
    },
  })

  await plugin['chat.message'](
    { sessionID: 'session-skill-expiry-compaction' },
    {
      message: { parts: [] },
      parts: [{ type: 'text', text: '压缩后的下一轮任务' }],
    },
  )

  const compactedOutput = { system: [] }
  await plugin['experimental.chat.system.transform'](
    { sessionID: 'session-skill-expiry-compaction', model: {} },
    compactedOutput,
  )

  const compactedInjected = compactedOutput.system.at(-1) ?? ''
  assert.doesNotMatch(compactedInjected, /Reusable skills from this session:/)
  assert.doesNotMatch(compactedInjected, /brainstorming/)
})
