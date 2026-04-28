const WORD_SEGMENTER = typeof Intl !== "undefined" && typeof Intl.Segmenter === "function"
  ? new Intl.Segmenter("und", { granularity: "word" })
  : null;

export const DEFAULT_MIN_RECOMMENDATION_SCORE = 1.5;
export const DEFAULT_MIN_TOP_SCORE_RATIO = 0.55;

export function createTokenizer({
  stopWords = new Set(),
  prepareText = (text) => text,
  partSplitPattern = /[._/\-+]+/g,
  useSegmenter = false,
  expandToken = (token) => [token],
} = {}) {
  return function tokenize(text = "") {
    const normalized = prepareText(String(text ?? "").normalize("NFKC").toLowerCase());
    const segments = useSegmenter && WORD_SEGMENTER
      ? Array.from(WORD_SEGMENTER.segment(normalized), (part) => part.segment)
      : normalized.split(/[^\p{L}\p{N}]+/u);

    const tokens = [];

    for (const segment of segments) {
      const parts = segment.split(partSplitPattern);
      for (const part of parts) {
        const token = part.trim();
        if (!token) continue;
        if (stopWords.has(token)) continue;
        if (token.length === 1 && !/^[0-9]$/.test(token)) continue;

        for (const expanded of expandToken(token) || []) {
          const nextToken = String(expanded ?? "").trim();
          if (!nextToken) continue;
          if (stopWords.has(nextToken)) continue;
          if (nextToken.length === 1 && !/^[0-9]$/.test(nextToken)) continue;
          tokens.push(nextToken);
        }
      }
    }

    return tokens;
  };
}

export function addTokens(weightMap, text, weight, tokenize) {
  for (const token of tokenize(text)) {
    weightMap.set(token, (weightMap.get(token) ?? 0) + weight);
  }
}

export function buildQueryWeights(text = "", intentKey = "unclear", options = {}) {
  const weights = new Map();
  const tokenize = options.tokenize;
  const intentTokenHints = options.intentTokenHints ?? {};
  const queryExpansionRules = options.queryExpansionRules ?? [];

  addTokens(weights, text, 1, tokenize);

  for (const token of intentTokenHints[intentKey] ?? []) {
    addTokens(weights, token, 0.75, tokenize);
  }

  for (const rule of queryExpansionRules) {
    if (rule.pattern.test(text)) {
      for (const token of rule.terms) {
        addTokens(weights, token, 0.9, tokenize);
      }
    }
  }

  return weights;
}

export function matchQueryTerms(queryWeights, searchText, tokenize) {
  const tokenSet = new Set(tokenize(searchText));
  const matches = [];

  for (const [token, weight] of queryWeights.entries()) {
    if (tokenSet.has(token)) {
      matches.push({ token, weight });
    }
  }

  matches.sort((left, right) => right.weight - left.weight || left.token.localeCompare(right.token));
  return matches;
}

export function rankCatalogEntries({
  text = "",
  catalog = [],
  limit = 3,
  intentKey = "unclear",
  minScore = DEFAULT_MIN_RECOMMENDATION_SCORE,
  minTopScoreRatio = DEFAULT_MIN_TOP_SCORE_RATIO,
  buildQueryWeights: buildWeights,
  scoreEntry,
  buildResult,
  onEmpty,
}) {
  const queryWeights = buildWeights(text, intentKey);

  const ranked = catalog
    .map((entry) => {
      const scored = scoreEntry(entry, queryWeights, text);
      return buildResult(entry, scored);
    })
    .filter((entry) => entry.score >= minScore)
    .sort((left, right) => right.score - left.score || left.name.localeCompare(right.name));

  if (!ranked.length) {
    return typeof onEmpty === "function" ? onEmpty({ text, catalog, limit, intentKey }) : [];
  }

  const topScore = ranked[0]?.score ?? 0;
  const cutoffScore = Math.max(minScore, topScore * minTopScoreRatio);
  return ranked.filter((entry) => entry.score >= cutoffScore).slice(0, limit);
}
