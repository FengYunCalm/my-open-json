import test from 'node:test'
import assert from 'node:assert/strict'

import { buildTaskRouting } from '../tool-forced-eval.helpers.mjs'
import { createMcpCatalogEntry } from '../tool-forced-eval.mcp.mjs'
import { buildSkillLookupRoots, loadSkillCatalog } from '../tool-forced-eval.skills.mjs'

const SKILL_CASES = [
  ['帮我先熟悉一下这个项目', 'project-init'],
  ['帮我定位这个函数是谁调用的', 'code-locator'],
  ['先给我一个实现计划和任务拆解', 'writing-plans'],
  ['这个线上问题根因怎么排查', 'systematic-debugging'],
  ['帮我写内部周报', 'internal-comms'],
  ['找一个 skill 处理 contract testing', 'contract-testing-builder'],
  ['给我做一个 Slack GIF', 'slack-gif-creator'],
  ['给我做一个海报封面', 'canvas-design'],
  ['给现有报告套一个主题', 'theme-factory'],
  ['给这个 HTML artifact 做复杂交互', 'web-artifacts-builder'],
  ['帮我写一个 Android 截图测试方案', 'android-testing'],
  ['这个 Jetpack Compose 页面怎么重构', 'compose-ui'],
  ['我要做一个 p5.js 生成艺术效果', 'algorithmic-art'],
  ['帮我共写一份 RFC 决策文档', 'doc-coauthoring'],
  ['帮我设计一个 MCP server 工具面', 'mcp-builder'],
  ['完成前帮我再验证一遍', 'verification-before-completion'],
  ['帮我做一个 Go 测试方案', 'golang-testing'],
  ['先看看有没有合适的 skill 处理这件事', 'find-skills'],
  ['用 Playwright 看看这个页面问题', 'webapp-testing'],
  ['帮我跑侠客行回归', 'ai-player'],
  ['帮我做一份游戏测试计划', 'gds-testing'],
  ['这个 Compose 列表卡顿怎么优化', 'compose-ui'],
  ['收到代码 review 反馈后帮我判断要不要改', 'receiving-code-review'],
  ['发布前做一轮回归检查', 'testing-regression'],
  ['把这个页面做得更有设计感', 'frontend-design'],
  ['像 Linear 一样重做这个管理后台', 'awesome-design'],
  ['帮我做一个 SaaS 仪表盘 UI/UX 方案', 'ui-ux-pro-max'],
  ['把这个页面做成 Anthropic 官方风格', 'brand-guidelines'],
  ['创建一个协作房间并导出聊天记录', 'relay-room'],
  ['起一个多代理协作团队', 'team-core'],
  ['给这个仓库建知识图谱', 'graphify'],
  ['这个分支要不要留着还是提PR', 'finishing-a-development-branch'],
  ['给这个产品页找一个参考设计风格', 'awesome-design'],
]

const MCP_CASES = [
  ['帮我查 React 官方文档', 'context7'],
  ['帮我查这个库最新的 API 用法', 'context7'],
  ['帮我搜开源仓库类似实现', 'grep_app'],
  ['帮我回顾之前的项目决策', 'evomemory'],
  ['帮我找一下之前记过的项目约束', 'evomemory'],
  ['帮我运行本地命令并检查进程', 'desktop_commander'],
  ['帮我抓取这个网页', 'fetch'],
  ['把这个网页抓下来', 'fetch'],
  ['创建一个 relay 协作房间', 'relay'],
  ['帮我起一个 relay thread', 'relay'],
  ['这个问题你分步骤推理一下', 'thinking'],
  ['帮我操作一下知识图谱关系', 'memory'],
  ['帮我去工作区外读取一个文件', 'filesystem'],
  ['帮我跑侠客行回归', 'xiakexing_ai'],
]

function loadInstalledSkillCatalog() {
  return loadSkillCatalog(buildSkillLookupRoots({
    globalConfigDir: '/home/mechrevo/.config/opencode',
    directory: '/home/mechrevo/.config/opencode',
    worktree: '/home/mechrevo/.config/opencode',
    homeDir: process.env.HOME || '',
  }))
}

function loadInstalledMcpCatalog() {
  return [
    'context7',
    'grep_app',
    'evomemory',
    'desktop_commander',
    'fetch',
    'relay',
    'thinking',
    'filesystem',
    'memory',
    'xiakexing_ai',
  ].map((name) => createMcpCatalogEntry(name, {}))
}

test('skill coverage matrix stays stable for high-value routing cases', () => {
  const catalog = loadInstalledSkillCatalog()

  for (const [text, expectedSkill] of SKILL_CASES) {
    const routing = buildTaskRouting(text, [], { shortlistLimit: 3 }, catalog)
    assert.equal(
      routing.skills[0]?.name,
      expectedSkill,
      `expected top skill ${expectedSkill} for: ${text}`,
    )
  }
})

test('mcp coverage matrix stays stable for high-value routing cases', () => {
  const catalog = loadInstalledMcpCatalog()

  for (const [text, expectedMcp] of MCP_CASES) {
    const routing = buildTaskRouting(text, catalog, { shortlistLimit: 3 }, [])
    assert.equal(
      routing.mcps[0]?.name,
      expectedMcp,
      `expected top MCP ${expectedMcp} for: ${text}`,
    )
  }
})
