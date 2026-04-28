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
  "a", "an", "and", "are", "as", "at", "be", "by", "can", "for", "from",
  "how", "i", "in", "is", "it", "of", "on", "or", "our", "the", "this",
  "to", "use", "using", "we", "what", "when", "where", "which", "who", "why",
  "with", "you", "your", "mcp", "server", "tool", "tools", "capability",
  "capabilities", "specialized", "enabled", "local", "remote", "的", "了", "和",
  "在", "请", "帮", "这个", "那个", "一个", "吗", "是", "我", "你",
]);

const INTENT_TOKEN_HINTS = {
  "memory-maintenance": ["memory", "feedback", "belief", "gene", "capsule", "maintain", "history"],
  history: ["memory", "history", "decisions", "preferences", "constraints", "feedback", "prior", "previous"],
  docs: ["docs", "documentation", "api", "reference", "manual", "sdk", "library", "framework", "context"],
  "oss-patterns": ["github", "open", "source", "repo", "example", "pattern", "grep"],
  "local-code": ["code", "source", "repo", "implementation", "locator"],
  "local-system": ["run", "execute", "shell", "terminal", "command", "process", "service", "desktop", "filesystem", "fetch"],
  reasoning: ["thinking", "reasoning", "analysis", "design", "architecture", "tradeoff", "debug", "review"],
  unclear: [],
};

const QUERY_EXPANSION_RULES = [
  { pattern: /(文档|官方文档|API|参考资料|用法|说明)/, terms: ["docs", "documentation", "api", "reference", "context"] },
  { pattern: /(GitHub|开源|同类项目|类似项目|示例仓库|示例项目)/, terms: ["github", "open", "source", "grep", "repo", "example"] },
  { pattern: /(历史|之前|先前|决策|偏好|约束|反馈|记忆)/, terms: ["history", "memory", "decisions", "preferences", "constraints", "feedback"] },
  { pattern: /(运行|执行|命令|终端|进程|服务|系统|桌面|文件系统)/, terms: ["run", "execute", "terminal", "process", "service", "desktop", "filesystem"] },
  { pattern: /(推理|分析|架构|设计|比较|取舍|排查)/, terms: ["thinking", "reasoning", "analysis", "architecture", "design", "debug"] },
  { pattern: /(侠客行|MUD|游戏|回归测试|玩法)/, terms: ["xiakexing", "ai", "player", "gameplay", "regression"] },
];

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const MCP_METADATA_PATH = path.join(__dirname, "tool-forced-eval.mcp.metadata.json");

function loadMcpMetadataOverrides() {
  try {
    const raw = fs.readFileSync(MCP_METADATA_PATH, "utf8");
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}

const MCP_METADATA_OVERRIDES = loadMcpMetadataOverrides();

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
  prepareText: (text) => text
    .replace(/([a-z])([A-Z0-9])/g, "$1 $2")
    .replace(/([0-9])([a-zA-Z])/g, "$1 $2")
    .replace(/[_./:-]+/g, " "),
  expandToken: (token) => token.endsWith("memory") && token !== "memory"
    ? [token, "memory"]
    : [token],
});

function titleCase(word = "") {
  if (!word) return "";
  return word[0].toUpperCase() + word.slice(1);
}

function humanizeName(name = "") {
  return name
    .replace(/([a-z])([A-Z0-9])/g, "$1 $2")
    .replace(/([0-9])([a-zA-Z])/g, "$1 $2")
    .replace(/[_-]+/g, " ")
    .split(/\s+/)
    .filter(Boolean)
    .map((part) => titleCase(part.toLowerCase()))
    .join(" ")
    .trim();
}

function buildQueryWeights(text = "", intentKey = "unclear") {
  return buildSharedQueryWeights(text, intentKey, {
    tokenize,
    intentTokenHints: INTENT_TOKEN_HINTS,
    queryExpansionRules: QUERY_EXPANSION_RULES,
  });
}

function collectCommandHints(entryConfig = {}) {
  if (!Array.isArray(entryConfig.command)) return "";
  return entryConfig.command
    .map((item) => {
      const value = String(item ?? "").trim();
      if (!value) return "";
      return `${value} ${path.basename(value)}`;
    })
    .filter(Boolean)
    .join(" ");
}

export function createMcpCatalogEntry(name, entryConfig = {}) {
  const mergedEntry = {
    ...(MCP_METADATA_OVERRIDES[name] && typeof MCP_METADATA_OVERRIDES[name] === "object" ? MCP_METADATA_OVERRIDES[name] : {}),
    ...(entryConfig && typeof entryConfig === "object" ? entryConfig : {}),
  };

  const summary = [mergedEntry.description, mergedEntry.summary, mergedEntry.purpose, mergedEntry.title]
    .find((value) => typeof value === "string" && value.trim())?.trim() || "specialized external tool capability";
  const rulePatterns = compileRulePatterns(mergedEntry.patterns);
  const rulePhrases = normalizeRulePhrases(mergedEntry.keywords);

  return {
    name,
    summary,
    reason: summary,
    rulePatterns,
    rulePhrases,
    ruleBoost: typeof mergedEntry.boost === "number" ? mergedEntry.boost : 0,
    searchText: [
      name,
      humanizeName(name),
      summary,
      typeof mergedEntry.note === "string" ? mergedEntry.note : "",
      typeof mergedEntry.type === "string" ? mergedEntry.type : "",
      collectCommandHints(mergedEntry),
    ].filter(Boolean).join("\n"),
  };
}

function matchQueryTerms(queryWeights, searchText) {
  return matchSharedQueryTerms(queryWeights, searchText, tokenize);
}

function buildReason(entry, matches, phraseMatches, patternMatched, score) {
  const tokens = [...new Set(matches.map((match) => match.token))].slice(0, 3);
  if (!tokens.length) {
    if (phraseMatches.length || patternMatched) {
      const phraseText = phraseMatches.slice(0, 2).map((phrase) => `\`${phrase}\``).join(", ");
      return `${entry.summary}. Strong configured trigger matched${phraseText ? ` on ${phraseText}` : ""}.`;
    }
    return entry.summary;
  }
  const confidence = score >= 3 ? "Strong match" : score >= 1.75 ? "Likely match" : "Possible match";
  return `${entry.summary}. ${confidence} on ${tokens.map((token) => `\`${token}\``).join(", ")}.`;
}

export function rankMcpRecommendations(text = "", catalog = [], options = {}) {
  const limit = options.limit ?? 3;
  const intentKey = options.intentKey ?? "unclear";

  return rankCatalogEntries({
    text,
    catalog,
    limit,
    intentKey,
    buildQueryWeights,
    scoreEntry: (entry, queryWeights, queryText) => {
      const matches = matchQueryTerms(queryWeights, entry.searchText || entry.name || "");
      const phraseMatches = matchesRulePhrases(entry.rulePhrases, queryText);
      const patternMatched = matchesRulePatterns(entry.rulePatterns, queryText);
      let score = 0;

      for (const match of matches) score += match.weight;

      if (phraseMatches.length) {
        score += 2.5 + (phraseMatches.length - 1) * 0.5;
      }

      if (phraseMatches.length || patternMatched) {
        score += entry.ruleBoost ?? 0;
      }

      if (patternMatched) {
        score += 3.5;
      }

      const normalizedQuery = queryText.normalize("NFKC").toLowerCase();
      const normalizedName = String(entry.name ?? "").normalize("NFKC").toLowerCase();
      if (normalizedName && normalizedQuery.includes(normalizedName)) score += 2.5;

      for (const token of tokenize(entry.name || "")) {
        if (queryWeights.has(token)) score += (queryWeights.get(token) ?? 0) * 1.25;
      }

      return { matches, phraseMatches, patternMatched, score };
    },
    buildResult: (entry, scored) => ({
      name: entry.name,
      reason: buildReason(entry, scored.matches, scored.phraseMatches, scored.patternMatched, scored.score),
      score: scored.score,
      triggerMatched: scored.phraseMatches.length > 0 || scored.patternMatched,
    }),
  });
}
