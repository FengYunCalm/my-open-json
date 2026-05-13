import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { execFile } from "node:child_process";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);
const runnerPath = path.resolve(
  "plugins",
  "tests",
  "evomemory_replay_runner.mjs",
);

async function runReplayCase(alias, summaryName) {
  const tempDir = await fs.mkdtemp(path.join(os.tmpdir(), "evomemory-replay-"));
  const summaryPath = path.join(tempDir, summaryName);
  await execFileAsync(process.execPath, [
    runnerPath,
    "--case",
    alias,
    "--summary",
    summaryPath,
  ]);
  const summary = JSON.parse(await fs.readFile(summaryPath, "utf8"));
  return { summary, summaryPath };
}

test("replay runner supports positive-preference case alias", async () => {
  const { summary } = await runReplayCase(
    "positive-preference",
    "positive.json",
  );

  assert.equal(summary.metrics.total_cases, 1);
  assert.equal(summary.metrics.failed_cases, 0);
  assert.deepEqual(summary.failed_cases, []);
  assert.equal(summary.cases.length, 1);
  assert.equal(summary.cases[0].id, "positive-user-preference-recall");
  assert.equal(summary.cases[0].trace.status, "ok");
  assert.equal(summary.cases[0].trace.session_id, "ses_replay_user_pref");
  assert.ok(summary.comparison.before.metrics);
});

test("replay runner supports negative-current-code case alias", async () => {
  const { summary } = await runReplayCase(
    "negative-current-code",
    "negative.json",
  );

  assert.equal(summary.metrics.total_cases, 1);
  assert.equal(summary.metrics.false_positive_injection_rate, 0);
  assert.deepEqual(summary.failed_cases, []);
  assert.equal(summary.cases.length, 1);
  assert.equal(summary.cases[0].id, "negative-no-memory-no-injection");
  assert.equal(summary.cases[0].injected, false);
  assert.equal(summary.cases[0].search_calls, 0);
  assert.equal(summary.cases[0].trace.status, "fail-open");
  assert.equal(
    summary.cases[0].trace.timeout_fallback_reason,
    "search_not_triggered",
  );
  assert.equal(summary.cases[0].trace.trigger_decision.should_search, false);
  assert.equal(summary.cases[0].trace.selected_count, 0);
  assert.ok(summary.comparison.before.metrics);
});

test("replay runner writes trace for every summary case", async () => {
  const { summary } = await runReplayCase("prompt-injection-memory", "trace.json");

  assert.equal(summary.cases.length, 1);
  assert.ok(summary.cases[0].trace);
  assert.equal(summary.cases[0].trace.search_type, "context_search");
  assert.ok(summary.cases[0].trace.candidate_count >= 1);
  assert.ok(
    summary.cases[0].trace.selected_count <=
      summary.cases[0].trace.candidate_count,
  );
  assert.equal(summary.cases[0].trace.redactions[0].label, "memory_text");
});

test("replay runner writes fail-open timeout trace evidence", async () => {
  const { summary } = await runReplayCase(
    "bridge-timeout-fail-open",
    "timeout.json",
  );
  const trace = summary.cases[0].trace;

  assert.equal(summary.metrics.total_cases, 1);
  assert.equal(summary.metrics.failed_cases, 0);
  assert.equal(summary.cases[0].injected, false);
  assert.equal(trace.status, "fail-open");
  assert.equal(trace.timeout_fallback_reason, "bridge_timeout");
  assert.equal(trace.request_timeout_ms, 15);
  assert.equal(trace.session_id, "ses_replay_timeout");
  assert.equal(trace.directory, "/fixtures/project-alpha");
  assert.equal(trace.wing, "opencode");
  assert.equal(trace.trigger_decision.should_search, true);
  assert.equal(trace.candidate_count, 0);
  assert.equal(trace.selected_count, 0);
  assert.deepEqual(trace.injection_budget_used, {
    characters: 0,
    estimated_tokens: 0,
  });
  assert.equal(trace.write_capture_decision, "message_flush_queued");
  assert.equal(trace.maintenance_action, "none");
});

test("replay runner keeps chosen_results empty when cross-project filtering removes all injected memory", async () => {
  const { summary } = await runReplayCase(
    "cross-project-leakage",
    "cross-project.json",
  );
  const trace = summary.cases[0].trace;

  assert.equal(summary.metrics.total_cases, 1);
  assert.equal(summary.metrics.failed_cases, 0);
  assert.equal(summary.cases[0].id, "cross-project-leakage");
  assert.equal(summary.cases[0].injected, false);
  assert.equal(trace.selected_count, 0);
  assert.deepEqual(trace.chosen_results, []);
});
