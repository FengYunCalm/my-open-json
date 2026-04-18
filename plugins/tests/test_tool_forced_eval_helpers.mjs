import test from 'node:test'
import assert from 'node:assert/strict'

import {
  buildTaskRouting,
  classifyIntent,
  detectSkillRecommendations,
  findGuardedBashCommand,
  isLikelySmallTalk,
  shouldInject,
} from '../tool-forced-eval.helpers.mjs'

test('filters english and chinese tiny small-talk without blocking substantive chinese requests', () => {
  assert.equal(isLikelySmallTalk('ok'), true)
  assert.equal(isLikelySmallTalk('好的'), true)
  assert.equal(isLikelySmallTalk('继续'), true)
  assert.equal(isLikelySmallTalk('继续分析这个实现'), false)
  assert.equal(shouldInject('谢谢'), false)
  assert.equal(shouldInject('继续分析这个实现'), true)
})

test('classifies the major task intents', () => {
  assert.equal(classifyIntent('use evomemory_record_feedback to correct stale beliefs').key, 'memory-maintenance')
  assert.equal(classifyIntent('请解释一下 plugins/tool-forced-eval.js 这个文件的当前实现').key, 'local-code')
  assert.equal(classifyIntent('look up the React useEffectEvent docs').key, 'docs')
  assert.equal(classifyIntent('go search similar OpenCode plugins on GitHub').key, 'oss-patterns')
  assert.equal(classifyIntent('what did we decide about project memory?').key, 'history')
  assert.equal(classifyIntent('run npm test and inspect the process').key, 'local-system')
  assert.equal(classifyIntent('compare the architecture tradeoffs').key, 'reasoning')
})

test('builds a short routed recommendation set', () => {
  const maintenanceRouting = buildTaskRouting('use evomemory_record_feedback to correct stale beliefs', ['evomemory', 'context7'], { shortlistLimit: 3 })
  assert.equal(maintenanceRouting.intent.key, 'memory-maintenance')
  assert.equal(maintenanceRouting.mcps[0]?.name, 'evomemory')

  const historyRouting = buildTaskRouting('review prior project decisions', ['evomemory', 'context7'], { shortlistLimit: 3 })
  assert.equal(historyRouting.intent.key, 'history')
  assert.equal(historyRouting.mcps[0]?.name, 'evomemory')

  const codeRouting = buildTaskRouting('学习一下 tool-forced-eval 这个插件源码', ['evomemory', 'context7'], { shortlistLimit: 3 })
  assert.equal(codeRouting.intent.key, 'local-code')
  assert.deepEqual(codeRouting.nativeTools.map((item) => item.name), ['glob', 'grep', 'read'])
})

test('detects relevant skill recommendations', () => {
  const debuggingSkills = detectSkillRecommendations('please debug this failing test suite', 3)
  assert.equal(debuggingSkills[0]?.name, 'systematic-debugging')

  const planSkills = detectSkillRecommendations('给我一个实施方案和任务拆解', 3)
  assert.equal(planSkills[0]?.name, 'writing-plans')
})

test('detects guarded bash commands without flagging safe commands', () => {
  assert.equal(findGuardedBashCommand('grep foo src'), 'grep')
  assert.equal(findGuardedBashCommand('find . -name package.json'), 'find')
  assert.equal(findGuardedBashCommand('cat README.md'), 'cat')
  assert.equal(findGuardedBashCommand('git grep foo'), null)
  assert.equal(findGuardedBashCommand('npm test'), null)
})
