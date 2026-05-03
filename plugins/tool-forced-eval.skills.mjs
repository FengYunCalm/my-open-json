import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import {
  buildQueryWeights as buildSharedQueryWeights,
  createTokenizer,
  matchQueryTerms as matchSharedQueryTerms,
  rankCatalogEntries,
} from "./tool-forced-eval.rank.mjs";

const STOP_WORDS = new Set([
  "a",
  "an",
  "and",
  "are",
  "as",
  "at",
  "be",
  "best",
  "by",
  "can",
  "common",
  "comprehensive",
  "could",
  "for",
  "from",
  "general",
  "generic",
  "guide",
  "guides",
  "guideline",
  "guidelines",
  "helper",
  "helpers",
  "how",
  "i",
  "in",
  "is",
  "it",
  "just",
  "me",
  "my",
  "of",
  "overview",
  "on",
  "or",
  "our",
  "please",
  "practice",
  "practices",
  "should",
  "skill",
  "skills",
  "so",
  "that",
  "the",
  "their",
  "this",
  "those",
  "to",
  "us",
  "use",
  "using",
  "we",
  "what",
  "when",
  "where",
  "which",
  "who",
  "why",
  "with",
  "would",
  "you",
  "your",
  "的",
  "了",
  "和",
  "与",
  "在",
  "请",
  "帮",
  "一下",
  "这个",
  "那个",
  "这些",
  "那些",
  "一个",
  "一些",
  "吗",
  "吧",
  "呢",
  "啊",
  "是",
  "我",
  "你",
  "我们",
  "你们",
  "他们",
  "它们",
]);

const DANGEROUS_PROMPT_PATTERNS = [
  /ignore\s+(all\s+)?previous\s+instructions?/gi,
  /reveal\s+(secrets?|tokens?|credentials?)/gi,
  /system\s+prompt/gi,
  /developer\s+(message|instructions?)/gi,
];

const QUERY_EXPANSION_RULES = [
  {
    pattern: /(方案|计划|实施步骤|任务拆解|实施)/,
    terms: ["plan", "implementation", "workflow", "tasks", "verification"],
  },
  {
    pattern: /(排查|报错|异常|复现|根因|故障)/,
    terms: ["debug", "bug", "failure", "reproduce", "root", "cause"],
  },
  {
    pattern: /(审查|代码检查|review)/,
    terms: ["review", "code", "changes", "tests"],
  },
  {
    pattern: /(测试|回归|验证)/,
    terms: ["test", "testing", "verification", "regression"],
  },
  {
    pattern: /(文档|官方文档|API|参考资料|用法|说明)/,
    terms: ["docs", "documentation", "api", "reference", "manual"],
  },
  {
    pattern: /(GitHub|开源|同类项目|类似项目|示例仓库|示例项目)/,
    terms: ["github", "open", "source", "similar", "example", "pattern"],
  },
  {
    pattern: /(当前实现|当前代码|源码|代码库|这个文件|这个函数|这个类|哪个文件|哪个函数|哪个类|模块|插件|实现细节)/,
    terms: ["current", "implementation", "code", "source", "file", "function", "class", "module", "plugin"],
  },
  {
    pattern: /(运行|执行|命令|终端|进程|服务|安装|时间|日期)/,
    terms: ["run", "execute", "shell", "terminal", "command", "process", "service", "install", "time", "date"],
  },
  {
    pattern: /(设计|架构|取舍|比较|为什么|重构)/,
    terms: ["design", "architecture", "tradeoff", "compare", "why", "refactor"],
  },
  {
    pattern: /(前端|页面|组件|样式|布局|界面|UI|UX|设计)/,
    terms: ["frontend", "ui", "ux", "component", "layout", "style", "design"],
  },
  {
    pattern: /(浏览器|Playwright|截图|DOM|控制台)/,
    terms: ["browser", "playwright", "screenshot", "dom", "console"],
  },
  {
    pattern: /(worktree|分支|拉取请求|PR|commit|branch)/i,
    terms: ["worktree", "branch", "pull", "request", "commit"],
  },
  {
    pattern: /(skill|skills|技能|工作流|插件|能力)/,
    terms: ["skill", "workflow", "plugin", "capability"],
  },
];

const INTENT_TOKEN_HINTS = {
  "memory-maintenance": ["memory", "feedback", "belief", "gene", "capsule", "reconcile", "maintain"],
  history: ["prior", "previous", "earlier", "past", "history", "decisions", "preferences", "constraints", "feedback", "benchmark"],
  docs: ["docs", "documentation", "api", "reference", "manual", "sdk", "library", "framework", "usage"],
  "oss-patterns": ["github", "open", "source", "similar", "repo", "example", "pattern"],
  "local-code": ["implementation", "source", "repo", "plugin", "locator", "inspect"],
  "local-system": ["run", "execute", "shell", "terminal", "command", "install", "process", "service", "date", "time"],
  reasoning: ["plan", "architecture", "tradeoff", "compare", "debug", "review", "refactor"],
  "unclear": [],
};

const POSITIVE_HEADING_PATTERNS = [
  /\bwhen to use\b/i,
  /\bmode selection\b/i,
  /\bdecision tree\b/i,
  /\bchoosing verification scope\b/i,
];

const NEGATIVE_HEADING_PATTERNS = [
  /\bboundaries\b/i,
  /\bred flags\b/i,
];

const POSITIVE_LINE_PATTERNS = [
  /\buse this skill when\b/i,
  /\buse when\b/i,
  /\bwhen the user\b/i,
  /\bwhen context is missing\b/i,
];

const NEGATIVE_LINE_PATTERNS = [
  /\bdo not use\b/i,
  /\bdo not\b/i,
  /\bdon't\b/i,
  /\bavoid\b/i,
  /\bnot as a ritual\b/i,
  /\bpause and clarify\b/i,
];

const SKILL_NAME_PATTERN = /^[a-z0-9]+(-[a-z0-9]+)*$/;
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SKILL_RULES_PATH = path.join(__dirname, "tool-forced-eval.skill-rules.json");

const ROOT_CACHE = new Map();

function loadSkillRuleOverrides() {
  try {
    const raw = fs.readFileSync(SKILL_RULES_PATH, "utf8");
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}

const SKILL_RULE_OVERRIDES = loadSkillRuleOverrides();

function compileRulePatterns(patterns = []) {
  if (!Array.isArray(patterns)) return [];
  const compiled = [];

  for (const pattern of patterns) {
    if (typeof pattern !== "string" || !pattern.trim()) continue;
    try {
      compiled.push(new RegExp(pattern, "i"));
    } catch {
      continue;
    }
  }

  return compiled;
}

function matchesRulePatterns(patterns = [], text = "") {
  return patterns.some((pattern) => pattern.test(text));
}

function normalizeRulePhrases(values = []) {
  if (!Array.isArray(values)) return [];
  return values
    .filter((value) => typeof value === "string")
    .map((value) => value.trim().toLowerCase())
    .filter(Boolean);
}

function matchesRulePhrases(phrases = [], text = "") {
  const normalizedText = String(text ?? "").normalize("NFKC").toLowerCase();
  return phrases.filter((phrase) => normalizedText.includes(phrase));
}

const tokenize = createTokenizer({
  stopWords: STOP_WORDS,
  useSegmenter: true,
});

function stripCodeBlocks(text) {
  return text.replace(/```[\s\S]*?```/g, " ");
}

function sanitizePromptText(text = "") {
  let sanitized = String(text ?? "")
    .replace(/<[^>]+>/g, " ")
    .replace(/[`]/g, "")
    .replace(/\b(?:system|developer|assistant|user)\s*:/gi, " ")
    .replace(/\s+/g, " ")
    .trim();
  for (const pattern of DANGEROUS_PROMPT_PATTERNS) {
    sanitized = sanitized.replace(pattern, "[redacted]");
  }
  return sanitized;
}

function collectAncestorDirs(directory = "", worktree = "") {
  if (!directory) return [];

  const resolvedDirectory = path.resolve(directory);
  const resolvedWorktree = worktree ? path.resolve(worktree) : "";
  const results = [];
  let current = resolvedDirectory;

  while (current) {
    results.push(current);
    if (resolvedWorktree && current === resolvedWorktree) break;

    const parent = path.dirname(current);
    if (parent === current) break;
    current = parent;
  }

  return results;
}

export function buildSkillLookupRoots({ globalConfigDir = "", directory = "", worktree = "", homeDir = "", customConfigDir = "" } = {}) {
  const roots = [];

  if (customConfigDir) {
    roots.push(path.join(customConfigDir, "skills"));
  }

  for (const currentDir of collectAncestorDirs(directory, worktree)) {
    roots.push(path.join(currentDir, ".opencode", "skills"));
    roots.push(path.join(currentDir, ".claude", "skills"));
    roots.push(path.join(currentDir, ".agents", "skills"));
  }

  if (globalConfigDir) {
    roots.push(path.join(globalConfigDir, "skills"));
  }

  if (homeDir) {
    roots.push(path.join(homeDir, ".claude", "skills"));
    roots.push(path.join(homeDir, ".agents", "skills"));
  }

  return [...new Set(roots.map((root) => path.resolve(root)))];
}

function stripFrontmatter(raw) {
  const normalized = raw.replace(/^\uFEFF/, "");
  const lines = normalized.split(/\r?\n/);
  let startIndex = 0;
  while (startIndex < lines.length && !lines[startIndex].trim()) {
    startIndex += 1;
  }

  if (lines[startIndex]?.trim() !== "---") {
    return { frontmatter: "", body: normalized };
  }

  let endIndex = -1;
  for (let index = startIndex + 1; index < lines.length; index += 1) {
    if (/^---\s*$/.test(lines[index])) {
      endIndex = index;
      break;
    }
  }

  if (endIndex === -1) {
    return { frontmatter: "", body: normalized };
  }

  return {
    frontmatter: lines.slice(startIndex + 1, endIndex).join("\n"),
    body: lines.slice(endIndex + 1).join("\n"),
  };
}

function stripQuotes(value) {
  const trimmed = value.trim();
  if ((trimmed.startsWith('"') && trimmed.endsWith('"')) || (trimmed.startsWith("'") && trimmed.endsWith("'"))) {
    return trimmed.slice(1, -1);
  }
  return trimmed;
}

function parseFrontmatter(frontmatter = "") {
  const result = {};
  let activeKey = "";
  let activeStyle = "literal";
  let activeLines = [];

  const flushActiveValue = () => {
    if (!activeKey) return;

    const value = activeStyle === "folded"
      ? collapseFoldedLines(activeLines)
      : activeLines.map((line) => line.replace(/\s+$/u, "")).join("\n").trim();

    result[activeKey] = value;
    activeKey = "";
    activeStyle = "literal";
    activeLines = [];
  };

  for (const rawLine of frontmatter.split(/\r?\n/)) {
    const line = rawLine.replace(/\r$/, "");

    if (activeKey) {
      if (!line.trim()) {
        activeLines.push("");
        continue;
      }

      if (/^[ \t]/.test(line)) {
        activeLines.push(line.replace(/^[ \t]+/, ""));
        continue;
      }

      flushActiveValue();
    }

    const match = line.match(/^([A-Za-z0-9_-]+):\s*(.*)$/);
    if (!match) continue;

    const key = match[1];
    const value = match[2].trim();

    if ((key === "name" || key === "description") && (value === "" || /^[|>]/.test(value))) {
      activeKey = key;
      activeStyle = value.startsWith(">") ? "folded" : "literal";
      activeLines = [];
      continue;
    }

    result[key] = stripQuotes(value);
  }

  flushActiveValue();

  return result;
}

function collapseFoldedLines(lines = []) {
  const paragraphs = [];
  let current = [];

  for (const line of lines) {
    if (!line.trim()) {
      if (current.length) {
        paragraphs.push(current.join(" "));
        current = [];
      }
      continue;
    }

    current.push(line.trim());
  }

  if (current.length) {
    paragraphs.push(current.join(" "));
  }

  return paragraphs.join("\n").trim();
}

function firstMeaningfulLine(text) {
  for (const line of text.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    if (trimmed.startsWith("#")) continue;
    if (trimmed.startsWith("```")) continue;
    return trimmed;
  }

  return "";
}

function truncate(text, limit = 180) {
  const trimmed = sanitizePromptText(text);
  if (trimmed.length <= limit) return trimmed;
  return `${trimmed.slice(0, limit - 1).trimEnd()}…`;
}

function splitMarkdownSections(body = "") {
  const sections = [];
  let current = { heading: "", lines: [] };

  for (const line of stripCodeBlocks(body).split(/\r?\n/)) {
    const headingMatch = line.match(/^#{2,3}\s+(.*)$/);
    if (headingMatch) {
      sections.push(current);
      current = {
        heading: headingMatch[1].trim(),
        lines: [],
      };
      continue;
    }

    current.lines.push(line);
  }

  sections.push(current);
  return sections
    .map((section) => ({
      heading: section.heading,
      text: section.lines.join("\n").trim(),
    }))
    .filter((section) => section.heading || section.text);
}

function collectSectionText(sections, headingPatterns, lineFilter = () => true) {
  return sections
    .filter((section) => headingPatterns.some((pattern) => pattern.test(section.heading)))
    .map((section) => section.text
      .split(/\r?\n/)
      .filter((line) => lineFilter(line.trim()))
      .join("\n")
      .trim())
    .filter(Boolean)
    .join("\n");
}

function collectMatchingLines(text, patterns, lineFilter = () => true) {
  return text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .filter((line) => lineFilter(line))
    .filter((line) => patterns.some((pattern) => pattern.test(line)))
    .join("\n");
}

function collectMeaningfulLines(text, limit = 4) {
  return text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .filter((line) => !line.startsWith("```"))
    .slice(0, limit);
}

function buildCompactBodyText(body = "") {
  return splitMarkdownSections(body)
    .map((section) => [
      section.heading,
      ...collectMeaningfulLines(section.text),
    ].filter(Boolean).join("\n"))
    .filter(Boolean)
    .join("\n");
}

function extractSkillSignals(body = "") {
  const sections = splitMarkdownSections(body);
  const positiveText = [
    collectSectionText(sections, POSITIVE_HEADING_PATTERNS, (line) => !NEGATIVE_LINE_PATTERNS.some((pattern) => pattern.test(line))),
    collectMatchingLines(body, POSITIVE_LINE_PATTERNS, (line) => !NEGATIVE_LINE_PATTERNS.some((pattern) => pattern.test(line))),
  ].filter(Boolean).join("\n");

  const negativeText = [
    collectSectionText(sections, NEGATIVE_HEADING_PATTERNS),
    collectMatchingLines(body, NEGATIVE_LINE_PATTERNS),
  ].filter(Boolean).join("\n");

  return {
    positiveText,
    negativeText,
  };
}

function buildQueryWeights(text, intentKey) {
  return buildSharedQueryWeights(text, intentKey, {
    tokenize,
    intentTokenHints: INTENT_TOKEN_HINTS,
    queryExpansionRules: QUERY_EXPANSION_RULES,
  });
}

function collectSkillFiles(rootDir, reportIssue = () => {}) {
  const results = [];
  if (!rootDir || !fs.existsSync(rootDir)) return results;

  let entries;
  try {
    entries = fs.readdirSync(rootDir, { withFileTypes: true });
  } catch (error) {
    reportIssue(rootDir, error);
    return results;
  }

  for (const entry of entries) {
    if (!entry.isDirectory()) continue;
    const skillFile = path.join(rootDir, entry.name, "SKILL.md");
    if (fs.existsSync(skillFile)) {
      results.push(skillFile);
    }
  }

  return results.sort((left, right) => left.localeCompare(right));
}

function isPlaceholderSkill(name = "", description = "", body = "") {
  const normalizedName = name.trim().toLowerCase();
  const normalizedDescription = description.trim().toLowerCase();
  const normalizedBody = body.trim().toLowerCase();

  return (
    normalizedName === "template-skill"
    || normalizedDescription === "replace with description of the skill and when claude should use it."
    || normalizedBody.startsWith("# insert instructions below")
  );
}

function isValidSkillDefinition(name = "", folderName = "") {
  if (!name || !folderName) return false;
  if (name.length > 64) return false;
  if (folderName !== name) return false;
  return SKILL_NAME_PATTERN.test(name);
}

function getFileFingerprint(filePath, reportIssue = () => {}) {
  try {
    const stat = fs.statSync(filePath);
    return {
      mtimeMs: stat.mtimeMs,
      size: stat.size,
    };
  } catch (error) {
    reportIssue(filePath, error);
    return null;
  }
}

function parseSkillFile(filePath, reportIssue = () => {}) {
  try {
    const raw = fs.readFileSync(filePath, "utf8");
    const { frontmatter, body } = stripFrontmatter(raw);
    const metadata = parseFrontmatter(frontmatter);
    const signals = extractSkillSignals(body);
    const compactBodyText = buildCompactBodyText(body);
    const folderName = path.basename(path.dirname(filePath));
    const name = metadata.name || folderName || path.basename(filePath, path.extname(filePath));
    const ruleOverride = SKILL_RULE_OVERRIDES[name] && typeof SKILL_RULE_OVERRIDES[name] === "object"
      ? SKILL_RULE_OVERRIDES[name]
      : {};
    const compiledRulePatterns = compileRulePatterns(ruleOverride.patterns);
    const rulePhrases = normalizeRulePhrases([
      ...(Array.isArray(ruleOverride.keywords) ? ruleOverride.keywords : []),
      ...(Array.isArray(ruleOverride.aliases) ? ruleOverride.aliases : []),
    ]);
    const description = metadata.description || firstMeaningfulLine(body);
    if (!metadata.name || !metadata.description) {
      return null;
    }
    if (!isValidSkillDefinition(name, folderName)) {
      return null;
    }
    if (isPlaceholderSkill(name, description, body)) {
      return null;
    }
    const searchText = [
      name,
      folderName,
      metadata.description || "",
      truncate(compactBodyText, 6000),
    ].join("\n");

    return {
      name,
      description: description ? truncate(description, 220) : "",
      sourcePath: filePath,
      searchText,
      rulePatterns: compiledRulePatterns,
      rulePhrases,
      ruleBoost: typeof ruleOverride.boost === "number" ? ruleOverride.boost : 0,
      ruleIntents: Array.isArray(ruleOverride.intents) ? ruleOverride.intents : [],
      positiveText: [
        signals.positiveText,
        Array.isArray(ruleOverride.when) ? ruleOverride.when.join("\n") : "",
      ].filter(Boolean).join("\n"),
      negativeText: [
        signals.negativeText,
        Array.isArray(ruleOverride.not_for) ? ruleOverride.not_for.join("\n") : "",
      ].filter(Boolean).join("\n"),
      summary: description ? truncate(description, 220) : truncate(firstMeaningfulLine(body) || name, 220),
    };
  } catch (error) {
    reportIssue(filePath, error);
    return null;
  }
}

export function loadSkillCatalog(skillRoots = [], reportIssue = () => {}, reportDuplicate = () => {}) {
  const resolvedRoots = [...new Set(skillRoots.filter(Boolean).map((root) => path.resolve(root)))];
  const catalog = new Map();

  for (const root of resolvedRoots) {
    const skillDir = path.basename(root) === "skills" ? root : path.join(root, "skills");
    const cacheKey = path.resolve(skillDir);
    const cachedRoot = ROOT_CACHE.get(cacheKey) ?? { files: new Map() };
    const nextFiles = new Map();

    for (const filePath of collectSkillFiles(cacheKey, reportIssue)) {
      const fingerprint = getFileFingerprint(filePath, reportIssue);
      if (!fingerprint) continue;

      const cachedFile = cachedRoot.files.get(filePath);
      let entry = cachedFile?.entry ?? null;

      // Re-read only files whose fingerprint changed.
      if (!cachedFile || cachedFile.mtimeMs !== fingerprint.mtimeMs || cachedFile.size !== fingerprint.size) {
        entry = parseSkillFile(filePath, reportIssue);
      }

      if (!entry?.name) continue;
      nextFiles.set(filePath, { ...fingerprint, entry });

      if (catalog.has(entry.name)) {
        reportDuplicate({
          name: entry.name,
          keptPath: catalog.get(entry.name)?.sourcePath,
          ignoredPath: filePath,
        });
        continue;
      }

      catalog.set(entry.name, entry);
    }

    ROOT_CACHE.set(cacheKey, { files: nextFiles });
  }

  return [...catalog.values()].sort((left, right) => left.name.localeCompare(right.name));
}

function isDiscoveryQuery(text = "") {
  return /\b(find\s+(a\s+)?skill|find\s+skills|discover\s+skills?|install\s+skills?|create\s+skill|is\s+there\s+(a|any)\s+skill|skill\s+for)\b/i.test(text)
    || /(找(一个|个)?技能|找skill|找skills|有没有(合适的)?技能|安装技能|创建技能|技能推荐|skill推荐)/.test(text);
}

function matchQueryTerms(queryWeights, skillText) {
  return matchSharedQueryTerms(queryWeights, skillText, tokenize);
}

function scoreSkill(skill, queryWeights, queryText, intentKey) {
  const matches = matchQueryTerms(queryWeights, skill.searchText);
  const ruleEnabled = !skill.ruleIntents?.length || skill.ruleIntents.includes(intentKey);
  const patternMatched = ruleEnabled && matchesRulePatterns(skill.rulePatterns, queryText);
  const phraseMatches = ruleEnabled ? matchesRulePhrases(skill.rulePhrases, queryText) : [];
  const positiveMatches = matchQueryTerms(queryWeights, skill.positiveText || "");
  const negativeMatches = matchQueryTerms(queryWeights, skill.negativeText || "");
  let score = 0;

  for (const match of matches) {
    score += match.weight;
  }

  if (phraseMatches.length) {
    score += 2.5 + (phraseMatches.length - 1) * 0.5;
  }

  if (phraseMatches.length || patternMatched) {
    score += skill.ruleBoost ?? 0;
  }

  if (patternMatched) {
    score += 3.5;
  }

  for (const match of positiveMatches) {
    score += match.weight * 0.85;
  }

  for (const match of negativeMatches) {
    score -= match.weight * 1.1;
  }

  const normalizedQuery = queryText.normalize("NFKC").toLowerCase();
  const normalizedName = skill.name.normalize("NFKC").toLowerCase();

  if (normalizedQuery.includes(normalizedName)) {
    score += 3;
  }

  for (const token of tokenize(skill.name)) {
    if (queryWeights.has(token)) {
      score += (queryWeights.get(token) ?? 0) * 1.5;
    }
  }

  return {
    matches,
    phraseMatches,
    patternMatched,
    positiveMatches,
    negativeMatches,
    score,
  };
}

function buildSkillReason(skill, matches, phraseMatches, patternMatched, positiveMatches, score) {
  const summary = skill.summary || skill.description || "Use this when it directly helps the task.";
  const preferredMatches = positiveMatches.length ? positiveMatches : matches;
  const matchedTokens = [...new Set(preferredMatches.map((match) => match.token))].slice(0, 3);

  if (!matchedTokens.length || patternMatched || phraseMatches.length) {
    if (patternMatched || phraseMatches.length) {
      const phraseText = phraseMatches.slice(0, 2).map((phrase) => `\`${phrase}\``).join(", ");
      return truncate(`${summary} Strong configured trigger matched${phraseText ? ` on ${phraseText}` : ""}.`, 220);
    }
    return truncate(summary, 220);
  }

  const matchText = matchedTokens.map((token) => `\`${token}\``).join(", ");
  const confidence = score >= 4 ? "Strong match" : score >= 2 ? "Likely match" : "Possible match";
  return truncate(`${summary} ${confidence} on ${matchText}.`, 260);
}

export function rankSkillRecommendations(text = "", catalog = [], options = {}) {
  const limit = options.limit ?? 3;
  const intentKey = options.intentKey ?? "unclear";
  const discoveryQuery = isDiscoveryQuery(text);

  return rankCatalogEntries({
    text,
    catalog,
    limit,
    intentKey,
    buildQueryWeights,
    scoreEntry: (skill, queryWeights, queryText) => scoreSkill(skill, queryWeights, queryText, intentKey),
    buildResult: (skill, scored) => ({
      name: skill.name,
      reason: buildSkillReason(skill, scored.matches, scored.phraseMatches, scored.patternMatched, scored.positiveMatches, scored.score),
      score: scored.score,
      triggerMatched: scored.phraseMatches.length > 0 || scored.patternMatched,
    }),
    onEmpty: () => {
      if (!discoveryQuery) return [];
      return catalog
        .map((skill) => ({
          name: skill.name,
          reason: truncate(skill.summary || skill.description || "Use this when it directly helps the task.", 260),
          score: 0,
        }))
        .slice(0, Math.max(limit, 6));
    },
  });
}
