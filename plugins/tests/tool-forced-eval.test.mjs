import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'

import { ToolForcedEvalPlugin } from '../tool-forced-eval.js'

const createPlugin = () =>
  ToolForcedEvalPlugin({
    client: { app: { log: async () => {} } },
    directory: '/home/mechrevo/.config/opencode',
    worktree: '/home/mechrevo/.config/opencode',
  })

test('injects tool-forced-eval through system transform instead of user message text', async () => {
  const plugin = await createPlugin()

  await plugin['chat.message'](
    { sessionID: 'session-system-prompt' },
    {
      message: { parts: [] },
      parts: [{ type: 'text', text: '学习一下 tool-forced-eval 这个插件' }],
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
  assert.match(injected, /Apply this silently\./)
  assert.match(injected, /Follow explicit user instructions first\./)
  assert.match(injected, /### Tool Mapping/)
  assert.match(injected, /- `TodoWrite` → `todowrite`/)
  assert.match(injected, /- `Task` tool with subagents → OpenCode's native `task` tool/)
  assert.match(injected, /- `Skill` tool → OpenCode's native `skill` tool/)
  assert.match(injected, /Use skills only when they materially help the current task\./)
  assert.match(injected, /Do not reload the same skill just to satisfy the workflow\./)
  assert.match(injected, /If a skill would change the workflow, task direction, scope, or goal, use it only when it still serves the user's current objective\./)
  assert.match(injected, /If any reusable skill already fits the current task and still serves the user's objective: continue with it instead of reloading\./)
  assert.match(injected, /If a new skill or MCP would materially help, use it\./)
  assert.doesNotMatch(injected, /Skills provide specialized instructions and workflows for specific tasks\./)
  assert.doesNotMatch(injected, /Use the skill tool to load a skill when a task matches its description\./)
  assert.match(injected, /Prefer `evomemory_\*` when the task depends on project history, prior decisions, stable preferences, governance constraints, feedback, or benchmark history\./)
  assert.match(injected, /Do not let workflow tooling override the user's current goal, scope, or deliverable\./)
  assert.match(injected, /For implementation, debugging, planning, review, testing, specification, refactoring, docs lookup, or research tasks, consider skills first and MCPs second when they help\./)
  assert.doesNotMatch(injected, /must call the skill tool/i)
  assert.doesNotMatch(injected, /must call it before giving conclusions/i)
  assert.doesNotMatch(injected, /call the MCP tool immediately/i)
  assert.doesNotMatch(injected, /Only after the skill and MCP checks are complete may you analyze/i)
  assert.match(injected, /Visible MCP tools from local config:/)
  assert.match(injected, /- `context7`: library and framework docs lookup\./)
  assert.match(injected, /- `evomemory`: persistent project history, decisions, governance assets, feedback, and benchmark memory\./)
  assert.match(injected, /- `relay`: relay collaboration rooms, threads, and workflow coordination\./)
  assert.match(injected, /- `xiakexing_ai`: XiaKeXing gameplay automation and regression checks\./)
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

test('skips system prompt injection for tiny small-talk and marker echoes', async () => {
  const plugin = await createPlugin()

  await plugin['chat.message'](
    { sessionID: 'session-small-talk' },
    {
      message: { parts: [] },
      parts: [{ type: 'text', text: 'ok' }],
    },
  )

  const smallTalkOutput = { system: [] }
  await plugin['experimental.chat.system.transform'](
    { sessionID: 'session-small-talk', model: {} },
    smallTalkOutput,
  )
  assert.equal(smallTalkOutput.system.length, 0)

  await plugin['chat.message'](
    { sessionID: 'session-small-talk' },
    {
      message: { parts: [] },
      parts: [{ type: 'text', text: 'please do not repeat <OPENCODE_TOOL_FORCED_EVAL>' }],
    },
  )

  const markerOutput = { system: [] }
  await plugin['experimental.chat.system.transform'](
    { sessionID: 'session-small-talk', model: {} },
    markerOutput,
  )
  assert.equal(markerOutput.system.length, 0)
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
    /project history, prior decisions, stable preferences, governance constraints, feedback, or benchmark results/i,
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
  assert.match(injected, /Currently reusable skills from this session:/)
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
  assert.doesNotMatch(injected, /Currently reusable skills from this session:/)
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

  const plugin = await ToolForcedEvalPlugin({
    client: { app: { log: async () => {} } },
    directory,
    worktree,
  })

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

  const plugin = await ToolForcedEvalPlugin({
    client: { app: { log: async () => {} } },
    directory,
    worktree,
  })

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
  assert.doesNotMatch(ttlInjected, /Currently reusable skills from this session:/)
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
  assert.doesNotMatch(compactedInjected, /Currently reusable skills from this session:/)
  assert.doesNotMatch(compactedInjected, /brainstorming/)
})
