import { rankSkillRecommendations } from "./tool-forced-eval.skills.mjs";
import { rankMcpRecommendations } from "./tool-forced-eval.mcp.mjs";

const SMALL_TALK_PATTERNS = [
  /^hi$/i,
  /^hello$/i,
  /^hey$/i,
  /^thanks?$/i,
  /^thank you$/i,
  /^ok$/i,
  /^okay$/i,
  /^continue$/i,
  /^start$/i,
  /^go$/i,
  /^yes$/i,
  /^no$/i,
  /^好$/,
  /^好的$/,
  /^好啊$/,
  /^行$/,
  /^行的$/,
  /^可以$/,
  /^收到$/,
  /^明白$/,
  /^了解$/,
  /^继续$/,
  /^开始$/,
  /^是$/,
  /^不是$/,
  /^谢谢$/,
  /^谢谢你$/,
  /^谢了$/,
  /^嗯$/,
  /^嗯嗯$/,
]

const HISTORY_HINTS = [
  /\b(prior|previous|earlier|past|history|historical|remember|remind|decisions?|preferences?|constraint|constraints|feedback|benchmark)\b/i,
  /\bwhat did we decide\b/i,
  /\bused to\b/i,
  /\bstable preferences?\b/i,
  /(之前|先前|以前|过去|历史|历史决策|偏好|约束|反馈|基准|记忆)/,
]

const DOCS_HINTS = [
  /\b(docs?|documentation|api reference|reference|manual|sdk|library|framework)\b/i,
  /\bhow do i use\b/i,
  /(文档|官方文档|API|参考资料|用法)/,
]

const MEMORY_MAINTENANCE_HINTS = [
  /\bevomemory_record_feedback\b/i,
  /\bevomemory_query_(beliefs|genes|capsules)\b/i,
  /\b(record|update|correct|fix|repair|delete|remove|reconcile|maintain)\s+(the\s+)?(durable memory|project memory|evomemory memory|belief|beliefs|gene|genes|capsule|capsules|feedback)\b/i,
  /\b(stale|incorrect)\s+(durable memory|project memory|belief|beliefs|gene|capsule|capsules)\b/i,
  /(记录|更新|修正|纠正|修补|删除|清理|维护).*(长期记忆|项目记忆|EvoMemory|belief|gene|capsule|反馈)/,
  /(过期|错误).*(长期记忆|项目记忆|EvoMemory|belief|gene|capsule)/,
]

const MEMORY_MAINTENANCE_EXCLUDES = [
  /\b(memory leak|memory usage|memory cache|cache invalidation|heap|gc|garbage collection)\b/i,
  /(内存泄漏|内存占用|内存缓存|缓存失效|缓存|堆内存|垃圾回收)/,
]

const OSS_HINTS = [
  /\b(github|open[- ]source|similar project|similar repo|example repos?|implementation pattern|public code)\b/i,
  /(GitHub|开源|同类项目|类似项目|类似实现|示例仓库|示例项目|同类插件)/,
]

const PROJECT_CONTEXT_HINTS = [
  /\b(project onboarding|project learning|repo audit|repository audit|code audit|architecture review|learn (this|the) (project|repo|repository|codebase)|familiarize (me )?with (this|the) (project|repo|repository|codebase))\b/i,
  /(学习|熟悉).*(项目|仓库|代码库|源码)/,
  /(审计|检查|梳理).*(项目|仓库|代码|插件|架构)/,
  /(项目学习|项目审计|代码审计|架构梳理|架构审查|熟悉仓库|熟悉项目)/,
]

const CURRENT_CODE_HINTS = [
  /\b(current implementation|current code|source code|codebase|repo|repository|module|plugin)\b/i,
  /\bexplain the current implementation\b/i,
  /\bshow me the current\b/i,
  /\b(which|what|this|that|the)\s+(file|function|class|module|plugin)\b/i,
  /\bline \d+\b/i,
  /[\w./-]+\.(js|jsx|ts|tsx|mjs|cjs|py|json|jsonc|md)\b/i,
  /(当前实现|当前代码|源码|代码库|项目源码|这个文件|这个函数|这个类|哪个文件|哪个函数|哪个类|模块|插件|第\d+行|实现细节)/,
]

const LOCAL_SYSTEM_HINTS = [
  /\b(run|execute|shell|bash|terminal|command|install|service|process|date|time|npm|pnpm|node|python)\b/i,
  /(运行|执行|命令|终端|进程|服务|安装|时间|日期)/,
]

const REASONING_HINTS = [
  /\b(plan|design|architecture|tradeoff|compare|reason|why|debug|review|refactor)\b/i,
  /(方案|设计|架构|取舍|比较|为什么|排查|审查|重构)/,
]

const NONTRIVIAL_LOCAL_CODE_HINTS = [
  /\b(debug|bug|failure|failing|regression|review|audit|refactor|architecture|design|plan|implement|change|fix|cross[- ]file|multi[- ]file)\b/i,
  /(排查|报错|失败|故障|回归|审查|审计|重构|架构|设计|方案|实现|修改|修复|多文件|跨文件)/,
]

const INTENT_LABELS = {
  'memory-maintenance': 'memory-maintenance',
  'history': 'history',
  'docs': 'docs',
  'oss-patterns': 'oss-patterns',
  'local-code': 'local-code',
  'local-system': 'local-system',
  'reasoning': 'reasoning',
  'unclear': 'unclear',
}

export function collectText(parts = []) {
  return parts
    .filter((part) => part?.type === 'text' && typeof part.text === 'string' && part.text.trim())
    .map((part) => part.text.trim())
    .join('\n\n')
}

export function isLikelySlashCommand(text = '') {
  const firstToken = text.trim().split(/\s+/)[0] || ''
  return /^\/[^/\s]+$/.test(firstToken)
}

export function isLikelySmallTalk(text = '') {
  const normalized = text.trim().replace(/[!?！？。,.]+$/g, '')
  if (!normalized) return true
  if (normalized.length > 24) return false
  return SMALL_TALK_PATTERNS.some((pattern) => pattern.test(normalized))
}

export function getInjectionSkipReason(text = '') {
  if (!text) return 'empty-text'
  if (text.includes('<OPENCODE_TOOL_FORCED_EVAL>') || text.includes('<OPENCODE_SKILL_FORCED_EVAL>')) {
    return 'marker-echo'
  }
  if (isLikelySlashCommand(text)) return 'slash-command'
  if (isLikelySmallTalk(text)) return 'small-talk'
  return null
}

export function shouldInject(text = '') {
  return getInjectionSkipReason(text) === null
}

function matchesAny(patterns, text) {
  return patterns.some((pattern) => pattern.test(text))
}

export function isProjectContextTask(text = '') {
  return matchesAny(PROJECT_CONTEXT_HINTS, text)
}

function shouldPreferEvomemory(text = '', intentKey = 'unclear') {
  if (['memory-maintenance', 'history'].includes(intentKey)) return true
  if (isProjectContextTask(text)) return true
  if (['local-code', 'reasoning'].includes(intentKey)) {
    return matchesAny(NONTRIVIAL_LOCAL_CODE_HINTS, text)
  }
  return false
}

export function classifyIntent(text = '') {
  if (!text.trim()) {
    return { key: 'unclear', label: INTENT_LABELS['unclear'], clear: false }
  }

  if (matchesAny(MEMORY_MAINTENANCE_HINTS, text) && !matchesAny(MEMORY_MAINTENANCE_EXCLUDES, text)) {
    return { key: 'memory-maintenance', label: INTENT_LABELS['memory-maintenance'], clear: true }
  }

  if (matchesAny(OSS_HINTS, text)) {
    return { key: 'oss-patterns', label: INTENT_LABELS['oss-patterns'], clear: true }
  }

  if (matchesAny(DOCS_HINTS, text)) {
    return { key: 'docs', label: INTENT_LABELS['docs'], clear: true }
  }

  if (matchesAny(CURRENT_CODE_HINTS, text)) {
    return { key: 'local-code', label: INTENT_LABELS['local-code'], clear: true }
  }

  if (matchesAny(HISTORY_HINTS, text)) {
    return { key: 'history', label: INTENT_LABELS['history'], clear: true }
  }

  if (matchesAny(LOCAL_SYSTEM_HINTS, text)) {
    return { key: 'local-system', label: INTENT_LABELS['local-system'], clear: true }
  }

  if (matchesAny(REASONING_HINTS, text)) {
    return { key: 'reasoning', label: INTENT_LABELS['reasoning'], clear: true }
  }

  return { key: 'unclear', label: INTENT_LABELS['unclear'], clear: false }
}

function dedupeByName(items = []) {
  const seen = new Set()
  const unique = []
  for (const item of items) {
    if (!item?.name || seen.has(item.name)) continue
    seen.add(item.name)
    unique.push(item)
  }
  return unique
}

export function detectSkillRecommendations(text = '', limit = 3, catalog = [], intentKey = 'unclear') {
  return dedupeByName(rankSkillRecommendations(text, catalog, { limit, intentKey }))
}

function buildNativeTool(name, reason) {
  return { name, reason }
}

function normalizeMcpCatalog(entries = []) {
  return entries
    .map((entry) => {
      if (typeof entry === 'string') {
        return {
          name: entry,
          summary: 'specialized external tool capability',
          reason: 'specialized external tool capability',
          searchText: entry,
        }
      }

      if (!entry || typeof entry !== 'object' || typeof entry.name !== 'string') return null
      return entry
    })
    .filter(Boolean)
}

export function buildTaskRouting(text = '', visibleMcpCatalog = [], config = {}, skillCatalog = []) {
  const intent = classifyIntent(text)
  const mcpCatalog = normalizeMcpCatalog(visibleMcpCatalog)
  const shortlistLimit = config.shortlistLimit ?? 3
  const projectContextTask = isProjectContextTask(text)
  const preferEvomemory = shouldPreferEvomemory(text, intent.key)
  const mcpShortlistLimit = preferEvomemory ? 2 : 1
  const nativeTools = []
  const rankedMcps = rankMcpRecommendations(text, mcpCatalog, { limit: mcpShortlistLimit, intentKey: intent.key })
  const evomemoryEntry = mcpCatalog.find((entry) => entry.name === 'evomemory')
  const evomemoryAwareMcps = (() => {
    if (!preferEvomemory || !evomemoryEntry || rankedMcps.some((mcp) => mcp.name === 'evomemory')) {
      return rankedMcps
    }
    const [evomemoryMcp] = rankMcpRecommendations(text, [evomemoryEntry], { limit: 1, intentKey: 'history' })
    if (!evomemoryMcp) return rankedMcps
    if (rankedMcps.length >= mcpShortlistLimit) return [rankedMcps[0], evomemoryMcp]
    return [...rankedMcps, evomemoryMcp]
  })()
  const mcps = dedupeByName(evomemoryAwareMcps).slice(0, mcpShortlistLimit)
  const skills = detectSkillRecommendations(text, shortlistLimit, skillCatalog, intent.key)

  let summary = 'No single tool family is clearly dominant. Prefer the smallest correct tool or skill for the task.'

  switch (intent.key) {
    case 'memory-maintenance':
      summary = 'Use EvoMemory to inspect existing context and keep durable memory current as the task confirms, corrects, or reconciles prior state.'
      break
    case 'history':
      summary = 'Prefer project memory for prior decisions and stable context, then read current code separately when implementation details matter.'
      break
    case 'docs':
      summary = 'Current library or framework docs are the source of truth for this task.'
      break
    case 'oss-patterns':
      summary = 'Look for public repository examples before reasoning from scratch.'
      break
    case 'local-code':
      summary = projectContextTask
        ? 'Inspect current code with native tools, and use EvoMemory for prior decisions or stable constraints before project learning, audit, or architecture conclusions.'
        : 'Inspect the local codebase with native workspace tools before reaching for MCPs.'
      nativeTools.push(buildNativeTool('glob', 'Find files by name or path pattern.'))
      nativeTools.push(buildNativeTool('grep', 'Search repository contents for symbols, strings, or patterns.'))
      nativeTools.push(buildNativeTool('read', 'Open only the relevant files and sections.'))
      break
    case 'local-system':
      summary = 'Use local execution tools for commands, process inspection, or heavyweight local file analysis.'
      nativeTools.push(buildNativeTool('bash', 'Run direct local commands when dedicated read/search tools are not a better fit.'))
      break
    case 'reasoning':
      summary = 'Use structured reasoning only when it materially helps a multi-step decision.'
      break
    default:
      nativeTools.push(buildNativeTool('glob', 'Find files by name when the task starts with repo exploration.'))
      nativeTools.push(buildNativeTool('grep', 'Search contents when the task starts with code discovery.'))
      nativeTools.push(buildNativeTool('read', 'Inspect the exact files after narrowing the search.'))
      break
  }

  return {
    intent,
    summary,
    nativeTools: dedupeByName(nativeTools).slice(0, shortlistLimit),
    mcps: dedupeByName(mcps),
    skills: dedupeByName(skills),
  }
}

export function findGuardedBashCommand(command = '', guardedCommands = ['grep', 'find', 'cat', 'head', 'tail']) {
  if (!command.trim()) return null

  const wrappedShell = command.match(
    /^(?:env\s+)?(?:[A-Za-z_][A-Za-z0-9_]*=\S+\s+)*(?:bash|sh|zsh|fish)\s+-[lc]+\s+(?<inner>[\s\S]+)$/i,
  )
  if (wrappedShell?.groups?.inner) {
    const inner = wrappedShell.groups.inner.trim()
    const unquoted =
      ((inner.startsWith('"') && inner.endsWith('"')) || (inner.startsWith("'") && inner.endsWith("'")))
        ? inner.slice(1, -1)
        : inner
    const nested = findGuardedBashCommand(unquoted, guardedCommands)
    if (nested) return nested
  }

  const escaped = guardedCommands.map((item) => item.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')
  const substitutionPattern = new RegExp(
    '(?:\\$\\(|`|\\()\\s*(?:command\\s+)?(?:[A-Za-z_][A-Za-z0-9_]*=\\S+\\s+|env\\s+)*(?<command>' + escaped + ')\\b',
    'i',
  )
  const substitutionMatch = substitutionPattern.exec(command)
  if (substitutionMatch?.groups?.command) {
    return substitutionMatch.groups.command.toLowerCase()
  }

  const pattern = new RegExp(
    `(?:^|(?:&&|\\|\\||\\||;)\\s*)(?:command\\s+)?(?:[A-Za-z_][A-Za-z0-9_]*=\\S+\\s+|env\\s+)*(?<command>${escaped})\\b`,
    'i',
  )
  return pattern.exec(command)?.groups?.command?.toLowerCase() ?? null
}
