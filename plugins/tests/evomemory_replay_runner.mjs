#!/usr/bin/env node

import assert from "node:assert/strict";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { performance } from "node:perf_hooks";

import { EvomemoryOpencodePlugin } from "../evomemory-opencode.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DEFAULT_FIXTURES = path.join(
  __dirname,
  "fixtures",
  "evomemory-replay",
  "cases.json",
);
const DEFAULT_SUMMARY = path.join(
  process.cwd(),
  ".sisyphus",
  "evidence",
  "evomemory-replay-summary.json",
);
const UNSAFE_PATTERNS = [
  /ignore\s+(all\s+)?previous\s+instructions?/i,
  /reveal\s+(secrets?|tokens?|credentials?)/i,
  /bearer\s+[a-z0-9._-]+/i,
  /api[_-]?key\s*[:=]/i,
];
const CASE_ALIASES = {
  "positive-preference": "positive-user-preference-recall",
  "positive-project-decision": "positive-project-decision-recall",
  "negative-current-code": "negative-no-memory-no-injection",
  "prompt-injection-memory": "prompt-injection-memory",
  "bridge-timeout-fail-open": "bridge-timeout-fail-open",
};
const DEFAULT_PLUGIN_CONFIG = path.join(
  __dirname,
  "..",
  "evomemory-opencode.config.json",
);
const TASK_1_BASELINE = Object.freeze({
  total_cases: 7,
  expected_hit_rate: 1,
  false_positive_injection_rate: 0.3333,
  unsafe_injection_count: 0,
  cross_namespace_leakage_count: 1,
  injected_budget: Object.freeze({
    total_characters: 1679,
    total_estimated_tokens: 421,
  }),
});
const TASK_1_BASELINE_SOURCE = Object.freeze({
  label: "task_1_replay_baseline_from_learnings",
  file: ".sisyphus/notepads/optimize-evomemory-agent-learning/learnings.md",
  evidence_section: "2026-05-12T00:51:59+08:00 Task 1 Replay Baseline",
  note: "Only historically verified Task 1 fields are populated below. Unrecovered baseline fields are intentionally omitted instead of being fabricated.",
});
const REPLAY_GATE_THRESHOLDS = Object.freeze({
  expected_hit_rate_min: 0.8,
  false_positive_injection_rate_max: 0.1,
  unsafe_injection_count_max: 0,
  cross_namespace_leakage_count_max: 0,
});

function parseArgs(argv) {
  const options = { summary: DEFAULT_SUMMARY, fixtures: DEFAULT_FIXTURES };
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "--summary") {
      options.summary = argv[++index];
    } else if (arg === "--fixtures") {
      options.fixtures = argv[++index];
    } else if (arg === "--case") {
      options.caseName = argv[++index];
    } else if (arg === "--help" || arg === "-h") {
      options.help = true;
    } else {
      throw new Error(`Unknown argument: ${arg}`);
    }
  }
  return options;
}

function usage() {
  return [
    "Usage: node plugins/tests/evomemory_replay_runner.mjs [--summary FILE] [--fixtures FILE] [--case ALIAS_OR_ID]",
    "Runs deterministic offline EvoMemory plugin replay cases and writes summary JSON.",
    "Aliases: positive-preference, positive-project-decision, negative-current-code, prompt-injection-memory, bridge-timeout-fail-open.",
  ].join("\n");
}

function jsonResponse(payload) {
  return {
    ok: true,
    json: async () => payload,
  };
}

function neverSettles() {
  return new Promise(() => {});
}

function makeMessage(testCase) {
  return {
    message: { id: `msg_${testCase.id}`, role: "user" },
    parts: [{ type: "text", text: testCase.prompt }],
  };
}

function countOccurrences(text, needle) {
  if (!needle) return 0;
  let count = 0;
  let position = 0;
  while (true) {
    const next = text.indexOf(needle, position);
    if (next === -1) return count;
    count += 1;
    position = next + needle.length;
  }
}

function hasUnsafeText(text) {
  return UNSAFE_PATTERNS.some((pattern) => pattern.test(text));
}

function outputText(output) {
  return Array.isArray(output.system) ? output.system.join("\n") : "";
}

function summarizeBudget(text) {
  return {
    characters: text.length,
    estimated_tokens: Math.ceil(text.length / 4),
  };
}

function containsForeignDirectory(memory, currentDirectory) {
  if (!memory || typeof memory !== "object") return false;
  if (memory.directory && memory.directory !== currentDirectory) return true;
  const collections = [
    memory.core_memory,
    memory.belief_memory,
    memory.results,
    memory.governance_assets?.genes,
    memory.governance_assets?.capsules,
  ];
  return collections.some((items) =>
    Array.isArray(items) &&
      items.some(
        (item) => item?.directory && item.directory !== currentDirectory,
      ),
  );
}

function buildFetch(testCase, calls) {
  return async (url, options = {}) => {
    const endpoint = String(url);
    calls.push({ url: endpoint, options });
    if (endpoint.endsWith("/health")) {
      return jsonResponse({ ok: true });
    }
    if (endpoint.endsWith("/internal/session/flush")) {
      return jsonResponse({ last_saved_message_id: `msg_${testCase.id}` });
    }
    if (endpoint.endsWith("/internal/context/search")) {
      if (testCase.bridgeMode === "timeout") return neverSettles();
      return jsonResponse(testCase.memories ?? { wing: "opencode", results: [] });
    }
    if (endpoint.endsWith("/internal/session/start")) {
      return jsonResponse({
        session_id: testCase.sessionID,
        directory: testCase.directory,
      });
    }
    throw new Error(`unexpected replay url for ${testCase.id}: ${endpoint}`);
  };
}

async function runReplayCase(testCase) {
  const calls = [];
  const logs = [];
  const plugin = await EvomemoryOpencodePlugin({
    client: {
      app: { log: async (entry) => logs.push(entry.body) },
      session: { messages: async () => ({ data: [] }) },
    },
    directory: testCase.directory,
    worktree: testCase.directory,
    configOverride: {
      bridgeBaseUrl: "http://127.0.0.1:8897",
      directBridgeCommand: [],
      ensureBridgeCommand: [],
      requestTimeoutMs: 15,
      searchRequestTimeoutMs: 15,
      traceSpineEnabled: true,
      preloadCoreMemory: false,
      maxInjectedChars: 2200,
      minRetrievalScore: 0.24,
      safeExcerptChars: 120,
    },
    fetchImpl: buildFetch(testCase, calls),
    sleepImpl: async () => {},
  });

  const start = performance.now();
  await plugin["chat.message"](
    { sessionID: testCase.sessionID },
    makeMessage(testCase),
  );
  const output = { system: [] };
  await plugin["experimental.chat.system.transform"](
    { sessionID: testCase.sessionID },
    output,
  );
  const elapsedMs = Number((performance.now() - start).toFixed(3));
  const rendered = outputText(output);
  const injected = rendered.length > 0;
  const expectedHits = testCase.expectedHits ?? [];
  const unexpectedHits = testCase.unexpectedHits ?? [];
  const missingExpectedHits = expectedHits.filter(
    (needle) => !rendered.includes(needle),
  );
  const presentUnexpectedHits = unexpectedHits.filter((needle) =>
    rendered.includes(needle),
  );
  const duplicateFailures = Object.entries(testCase.maxOccurrences ?? {})
    .map(([needle, max]) => ({
      needle,
      max,
      actual: countOccurrences(rendered, needle),
    }))
    .filter((item) => item.actual > item.max);
  const unsafe = hasUnsafeText(rendered);
  const lastTrace = logs
    .map((entry) => entry?.extra?.trace)
    .filter(Boolean)
    .at(-1);
  const crossNamespaceLeakage =
    containsForeignDirectory(testCase.memories, testCase.directory) && injected;
  const failures = [];
  if (testCase.expectInjection !== injected) {
    failures.push({
      kind: "injection_expectation",
      expected: testCase.expectInjection,
      actual: injected,
    });
  }
  for (const needle of missingExpectedHits) {
    failures.push({ kind: "missing_expected_hit", needle });
  }
  for (const needle of presentUnexpectedHits) {
    failures.push({ kind: "unexpected_hit", needle });
  }
  for (const failure of duplicateFailures) {
    failures.push({ kind: "duplicate_memory", ...failure });
  }
  if (testCase.expectUnsafe !== unsafe) {
    failures.push({
      kind: "unsafe_injection",
      expected: testCase.expectUnsafe,
      actual: unsafe,
    });
  }
  if (testCase.expectCrossNamespaceLeakage !== crossNamespaceLeakage) {
    failures.push({
      kind: "cross_namespace_leakage",
      expected: testCase.expectCrossNamespaceLeakage,
      actual: crossNamespaceLeakage,
    });
  }

  return {
    id: testCase.id,
    description: testCase.description,
    passed: failures.length === 0,
    injected,
    expected_hit_count: expectedHits.length,
    observed_expected_hit_count:
      expectedHits.length - missingExpectedHits.length,
    false_positive_count: presentUnexpectedHits.length,
    unsafe_injection: unsafe,
    cross_namespace_leakage: crossNamespaceLeakage,
    added_latency_ms: elapsedMs,
    injected_budget: summarizeBudget(rendered),
    trace: lastTrace ?? null,
    search_calls: calls.filter((call) =>
      call.url.endsWith("/internal/context/search"),
    ).length,
    flush_calls: calls.filter((call) =>
      call.url.endsWith("/internal/session/flush"),
    ).length,
    failures,
    logs: logs.map((entry) => entry?.message).filter(Boolean),
  };
}

function calculateMetrics(cases) {
  const expectedTotal = cases.reduce(
    (sum, item) => sum + item.expected_hit_count,
    0,
  );
  const observedExpected = cases.reduce(
    (sum, item) => sum + item.observed_expected_hit_count,
    0,
  );
  const injectionEligible = cases.filter((item) => item.expected_hit_count > 0);
  const falsePositiveEligible = cases.filter(
    (item) => item.expected_hit_count === 0,
  );
  const falsePositiveInjected = falsePositiveEligible.filter(
    (item) => item.injected,
  ).length;
  const addedLatencyValues = cases.map((item) => item.added_latency_ms);
  const charValues = cases.map((item) => item.injected_budget.characters);
  const tokenValues = cases.map((item) => item.injected_budget.estimated_tokens);
  const total = (values) => values.reduce((sum, value) => sum + value, 0);
  const average = (values) =>
    values.length ? Number((total(values) / values.length).toFixed(3)) : 0;
  return {
    total_cases: cases.length,
    passed_cases: cases.filter((item) => item.passed).length,
    failed_cases: cases.filter((item) => !item.passed).length,
    expected_hit_rate:
      expectedTotal > 0
        ? Number((observedExpected / expectedTotal).toFixed(4))
        : 1,
    false_positive_injection_rate:
      falsePositiveEligible.length > 0
        ? Number((falsePositiveInjected / falsePositiveEligible.length).toFixed(4))
        : 0,
    unsafe_injection_count: cases.filter((item) => item.unsafe_injection).length,
    cross_namespace_leakage_count: cases.filter(
      (item) => item.cross_namespace_leakage,
    ).length,
    added_latency_ms: {
      total: Number(total(addedLatencyValues).toFixed(3)),
      average: average(addedLatencyValues),
      max: Number(Math.max(0, ...addedLatencyValues).toFixed(3)),
    },
    injected_budget: {
      total_characters: total(charValues),
      average_characters: average(charValues),
      total_estimated_tokens: total(tokenValues),
      average_estimated_tokens: average(tokenValues),
    },
    injection_eligible_cases: injectionEligible.length,
    injected_cases: cases.filter((item) => item.injected).length,
  };
}

function buildComparison(metrics) {
  const before = {
    label: "before_optimization_task_1_baseline",
    metrics: TASK_1_BASELINE,
  };
  const after = {
    label: "after_tasks_2_to_9_final",
    metrics,
  };
  const candidateRegressions = [];
  if (metrics.expected_hit_rate < TASK_1_BASELINE.expected_hit_rate) {
    candidateRegressions.push({
      metric: "expected_hit_rate",
      baseline: TASK_1_BASELINE.expected_hit_rate,
      current: metrics.expected_hit_rate,
      reason: "Current replay hit rate fell below the Task 1 baseline.",
    });
  }
  if (
    metrics.false_positive_injection_rate >
    TASK_1_BASELINE.false_positive_injection_rate
  ) {
    candidateRegressions.push({
      metric: "false_positive_injection_rate",
      baseline: TASK_1_BASELINE.false_positive_injection_rate,
      current: metrics.false_positive_injection_rate,
      reason: "Current replay injected more false positives than the Task 1 baseline.",
    });
  }
  if (metrics.unsafe_injection_count > TASK_1_BASELINE.unsafe_injection_count) {
    candidateRegressions.push({
      metric: "unsafe_injection_count",
      baseline: TASK_1_BASELINE.unsafe_injection_count,
      current: metrics.unsafe_injection_count,
      reason: "Current replay surfaced more unsafe injections than the Task 1 baseline.",
    });
  }
  if (
    metrics.cross_namespace_leakage_count >
    TASK_1_BASELINE.cross_namespace_leakage_count
  ) {
    candidateRegressions.push({
      metric: "cross_namespace_leakage_count",
      baseline: TASK_1_BASELINE.cross_namespace_leakage_count,
      current: metrics.cross_namespace_leakage_count,
      reason: "Current replay leaked more cross-namespace memories than the Task 1 baseline.",
    });
  }
  if (
    metrics.injected_budget.total_characters >
    TASK_1_BASELINE.injected_budget.total_characters
  ) {
    candidateRegressions.push({
      metric: "injected_budget.total_characters",
      baseline: TASK_1_BASELINE.injected_budget.total_characters,
      current: metrics.injected_budget.total_characters,
      reason: "Current replay used a larger injected character budget than the Task 1 baseline.",
    });
  }
  if (
    metrics.injected_budget.total_estimated_tokens >
    TASK_1_BASELINE.injected_budget.total_estimated_tokens
  ) {
    candidateRegressions.push({
      metric: "injected_budget.total_estimated_tokens",
      baseline: TASK_1_BASELINE.injected_budget.total_estimated_tokens,
      current: metrics.injected_budget.total_estimated_tokens,
      reason: "Current replay used a larger injected token budget than the Task 1 baseline.",
    });
  }
  return {
    baseline_source: TASK_1_BASELINE_SOURCE,
    before,
    after,
    candidate_regressions: candidateRegressions,
  };
}

function buildGateEvaluation(metrics, replayConfig) {
  const checks = {
    expected_hit_rate: {
      operator: ">=",
      threshold: REPLAY_GATE_THRESHOLDS.expected_hit_rate_min,
      observed: metrics.expected_hit_rate,
      passed:
        metrics.expected_hit_rate >= REPLAY_GATE_THRESHOLDS.expected_hit_rate_min,
    },
    false_positive_injection_rate: {
      operator: "<=",
      threshold: REPLAY_GATE_THRESHOLDS.false_positive_injection_rate_max,
      observed: metrics.false_positive_injection_rate,
      passed:
        metrics.false_positive_injection_rate <=
        REPLAY_GATE_THRESHOLDS.false_positive_injection_rate_max,
    },
    unsafe_injection_count: {
      operator: "==",
      threshold: REPLAY_GATE_THRESHOLDS.unsafe_injection_count_max,
      observed: metrics.unsafe_injection_count,
      passed:
        metrics.unsafe_injection_count ===
        REPLAY_GATE_THRESHOLDS.unsafe_injection_count_max,
    },
    cross_namespace_leakage_count: {
      operator: "==",
      threshold: REPLAY_GATE_THRESHOLDS.cross_namespace_leakage_count_max,
      observed: metrics.cross_namespace_leakage_count,
      passed:
        metrics.cross_namespace_leakage_count ===
        REPLAY_GATE_THRESHOLDS.cross_namespace_leakage_count_max,
    },
    added_latency_ms_max: {
      operator: "<=",
      threshold: replayConfig.request_timeout_ms,
      observed: metrics.added_latency_ms.max,
      passed: metrics.added_latency_ms.max <= replayConfig.request_timeout_ms,
      threshold_source: replayConfig.source,
    },
  };
  return {
    all_passed: Object.values(checks).every((item) => item.passed),
    policy_sources: [
      ".sisyphus/plans/optimize-evomemory-agent-learning.md",
      "mcp/evomemory/README.md",
      replayConfig.source,
    ],
    checks,
  };
}

async function loadCases(fixturesPath) {
  const raw = await fs.readFile(fixturesPath, "utf8");
  const parsed = JSON.parse(raw);
  assert.ok(Array.isArray(parsed), "Replay fixtures must be an array");
  return parsed;
}

async function loadReplayConfig(configPath = DEFAULT_PLUGIN_CONFIG) {
  const relativePath = path.relative(process.cwd(), configPath);
  try {
    const raw = await fs.readFile(configPath, "utf8");
    const parsed = JSON.parse(raw);
    const configuredTimeout = Number(parsed.requestTimeoutMs ?? 5000);
    return {
      request_timeout_ms:
        Number.isFinite(configuredTimeout) && configuredTimeout > 0
          ? configuredTimeout
          : 5000,
      source: relativePath,
    };
  } catch {
    return {
      request_timeout_ms: 5000,
      source: relativePath,
    };
  }
}

function resolveCaseID(caseName) {
  if (!caseName) return null;
  return CASE_ALIASES[caseName] ?? caseName;
}

function selectCases(cases, caseName) {
  const caseID = resolveCaseID(caseName);
  if (!caseID) return cases;
  const selected = cases.filter((testCase) => testCase.id === caseID);
  if (!selected.length) {
    const knownAliases = Object.keys(CASE_ALIASES).join(", ");
    const knownIDs = cases.map((testCase) => testCase.id).join(", ");
    throw new Error(
      `Unknown replay case '${caseName}'. Known aliases: ${knownAliases}. Known ids: ${knownIDs}.`,
    );
  }
  return selected;
}

async function writeSummary(summaryPath, payload) {
  await fs.mkdir(path.dirname(summaryPath), { recursive: true });
  await fs.writeFile(summaryPath, `${JSON.stringify(payload, null, 2)}\n`);
}

async function main() {
  const options = parseArgs(process.argv.slice(2));
  if (options.help) {
    console.log(usage());
    return;
  }
  const fixturesPath = path.resolve(options.fixtures);
  const summaryPath = path.resolve(options.summary);
  const replayConfig = await loadReplayConfig();
  const cases = selectCases(await loadCases(fixturesPath), options.caseName);
  const results = [];
  for (const testCase of cases) {
    results.push(await runReplayCase(testCase));
  }
  const metrics = calculateMetrics(results);
  assert.equal(
    results.filter((item) => item.trace).length,
    results.length,
    "Replay summary must include trace for every case",
  );
  const failedCases = results
    .filter((item) => !item.passed)
    .map((item) => ({
      id: item.id,
      description: item.description,
      failures: item.failures,
    }));
  const summary = {
    schema_version: 1,
    generated_at: "2026-05-12T00:00:00.000Z",
    runner: "plugins/tests/evomemory_replay_runner.mjs",
    offline: true,
    fixtures: path.relative(process.cwd(), fixturesPath),
    metrics,
    failed_cases: failedCases,
    comparison: buildComparison(metrics),
    gate_evaluation: buildGateEvaluation(metrics, replayConfig),
    cases: results.map(({ logs, ...item }) => item),
  };
  await writeSummary(summaryPath, summary);
  console.log(
    JSON.stringify(
      {
        summary: path.relative(process.cwd(), summaryPath),
        metrics,
        failed_cases: failedCases.map((item) => item.id),
      },
      null,
      2,
    ),
  );
}

main().catch((error) => {
  console.error(error?.stack || error);
  process.exitCode = 1;
});
