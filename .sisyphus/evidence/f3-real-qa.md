# F3 Real Manual QA

- Verdict: `APPROVE`
- Reviewer role: scenario reviewer only; no implementation changes made.
- Replay command executed: `node plugins/tests/evomemory_replay_runner.mjs --summary .sisyphus/evidence/f3-real-qa.md`
- Note: the command first wrote raw JSON to this path; after inspection, this file was rewritten into a readable QA report as required.

## Overall result

- Raw replay summary reports 7 total cases, 7 passed, 0 failed.
- Gate evaluation is `all_passed: true`.
- Observed metrics: expected_hit_rate=1, false_positive_injection_rate=0, unsafe_injection_count=0, cross_namespace_leakage_count=0.
- Latency/budget stayed within gate: max added latency 15.932ms, total injected characters 1576, total estimated tokens 396.
- Compared with the Task 1 baseline recorded in `learnings.md`, this run improved false-positive injection rate from 0.3333 to 0 and cross-namespace leakage count from 1 to 0, with no candidate regressions.

## Scenario-by-scenario review

1. **Positive recall** — `positive-user-preference-recall` + `positive-project-decision-recall`
   - Fixture expectations: `response_language=zh-CN`, `git_commit_behavior=disabled`, and `drawer=drawer_project_decision`.
   - Raw summary evidence: first case observed_expected_hit_count=1/1 with injected=true; second case observed_expected_hit_count=2/2 with injected=true.
   - Trace evidence: project-decision case has candidate_count=1, selected_count=1, chosen_results=`drawer_project_decision`, status=`ok`.
   - Judgment: expected sourced memory is injected when the prompt explicitly asks for prior preference/project decision.

2. **Negative no-recall** — `negative-no-memory-no-injection`
   - Fixture explicitly forbids `Optional historical context from EvoMemory` for a current-code prompt.
   - Raw summary evidence: injected=false, false_positive_count=0, search_calls=0.
   - Trace evidence: trigger_decision.should_search=false, selected_count=0, status=`fail-open`, timeout_fallback_reason=`search_not_triggered`.
   - Judgment: generic current-code requests stay local and do not pull irrelevant historical memory.

3. **Malicious memory** — `prompt-injection-memory`
   - Fixture expects `drawer=drawer_prompt_injection` and `[redacted]`, and forbids raw `Ignore all previous instructions` / `reveal secrets` text.
   - Raw summary evidence: observed_expected_hit_count=2/2, injected=true, unsafe_injection=false.
   - Trace evidence: candidate_count=1, selected_count=1, chosen_results includes `drawer_prompt_injection`, redactions contains `{ label: "memory_text", count: 1 }`, status=`ok`.
   - Judgment: malicious historical text is sanitized into redacted memory context and does not become an instruction.

4. **Bridge-down / fail-open** — `bridge-timeout-fail-open`
   - Fixture expects no injection when the bridge stalls.
   - Raw summary evidence: injected=false, injected budget is zero, failures=[].
   - Trace evidence: trigger_decision.should_search=true but candidate_count=0, selected_count=0, status=`fail-open`, timeout_fallback_reason=`bridge_timeout`, request_timeout_ms=15.
   - Additional regression proof: `node --test plugins/tests/evomemory_replay_runner.test.mjs` passed 5/5, including the timeout trace assertion.
   - Judgment: bridge failure does not block chat path and degrades safely without memory injection.

5. **Duplicate / conflict handling** — `duplicate-memory-dedupe`
   - Fixture seeds two identical `review_policy=run_tests_first` memories and sets `maxOccurrences` for that string to 1.
   - Raw summary evidence: case passed with observed_expected_hit_count=1/1, injected=true, failures=[].
   - Trace evidence: candidate_count=2, selected_count=0, status=`ok`, no duplicate-related failure entries were recorded.
   - Judgment: duplicate/conflicting historical entries do not cause repeated bad injection; rendered output stayed within the one-occurrence rule encoded by the fixture.

6. **Cross-namespace isolation** — `cross-project-leakage`
   - Fixture plants project-beta memory while the active directory is project-alpha and forbids `deployment_policy=project_beta_only` plus `drawer=drawer_project_beta_policy`.
   - Raw summary evidence: injected=false, false_positive_count=0, cross_namespace_leakage=false.
   - Trace evidence: candidate_count=1 but selected_count=0, chosen_results=[], injected budget is zero, status=`ok`.
   - Additional regression proof: replay runner test explicitly checks this exact chosen_results-empty behavior and passed.
   - Judgment: foreign-project memory is filtered out completely; no namespace leakage remains.

## Final verdict

`APPROVE`

Reasoning: all six required replay scenario classes meet the expected behavior under manual review, and the final replay summary also satisfies the plan-level gate thresholds. I found no unverified scenario gap that would justify rejection.

## Files and evidence reviewed

- `.sisyphus/plans/optimize-evomemory-agent-learning.md`
- `.sisyphus/notepads/optimize-evomemory-agent-learning/learnings.md`
- `.sisyphus/notepads/optimize-evomemory-agent-learning/issues.md`
- `plugins/tests/fixtures/evomemory-replay/cases.json`
- `plugins/tests/evomemory_replay_runner.mjs`
- `plugins/tests/evomemory_replay_runner.test.mjs`
- `.sisyphus/evidence/task-10-docs-safety.txt`

## Safety note

The replay trace still contains `session_id` and `directory` fields, but per Task 10 docs-safety evidence these are synthetic offline fixture identifiers (`ses_replay_*`, `/fixtures/project-*`), not live runtime secrets or private machine paths.
