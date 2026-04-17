import test from 'node:test'
import assert from 'node:assert/strict'

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
  assert.match(injected, /If a relevant skill is already reusable in the current context, reuse it instead of loading it again\./)
  assert.match(injected, /Do not reload the same skill just to satisfy the workflow\./)
  assert.match(injected, /If there is even a 1 percent chance that a new skill applies, you must call the skill tool\./)
  assert.match(injected, /If any reusable skill already fits: continue with it instead of reloading\./)
  assert.match(injected, /If any new skill applies: call the skill tool immediately\./)
  assert.doesNotMatch(injected, /Skills provide specialized instructions and workflows for specific tasks\./)
  assert.doesNotMatch(injected, /Use the skill tool to load a skill when a task matches its description\./)
  assert.match(injected, /For implementation, debugging, planning, review, testing, specification, refactoring, docs lookup, or research tasks, default to checking skills first and MCP second\./)
  assert.match(injected, /If any enabled MCP tool applies, you must call it before giving conclusions\./)
  assert.match(injected, /If any MCP applies: call the MCP tool immediately before answering\./)
  assert.match(injected, /Visible MCP tools from local config:/)
  assert.match(injected, /- `context7`: library and framework docs lookup\./)
  assert.match(injected, /- `evomemory`: persistent project memory, decisions, governance assets, and benchmark history\./)
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

test('only adds tool guidance for MCPs that still opt in', async () => {
  const plugin = await createPlugin()

  const context7Output = { description: 'Query docs', parameters: {} }
  await plugin['tool.definition']({ toolID: 'context7_query-docs' }, context7Output)
  assert.match(context7Output.description, /Plugin guidance:/)

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
