# Describe → Generate → Simulate → Review → Activate → Enforce

Policy Lab is an operator terminal workflow, added to the existing Guardian plugin. It reuses `guardian.policy.Policy` unchanged. The runtime evaluator, hook adapter and audit implementation from `guardian-stable` are unchanged. There is no dashboard, cloud service, mandatory API key or new dependency.

## Start with a proposal

After installing/enabling Guardian and restarting Hermes, the public plugin CLI is available:

```sh
hermes guardian propose 'Hermes can edit my coding projects, but must ask before deleting files or pushing code to GitHub.'
```

This asks focused clarification questions. The current schema does **not** support project-scoped positive permissions or approval for `git push`. It cannot safely translate that sentence literally. The conservative choice is approval for edits everywhere, approval for the supported terminal grammar (including deletion), and blocking Git commands. To choose it explicitly:

```sh
hermes guardian propose 'Ask before edits and deletions; block GitHub pushes.' --output /absolute/operator/path/proposal.json
```

The offline builder is an **exact, case-insensitive language template**, not a general natural-language model. Other wording produces clarification questions and cannot activate. It retains stronger existing tool rules and all existing protected-path rules. If a baseline already blocks reads or edits, this template will not silently allow them; simulation shows the difference.

`--output` requires an interactive `SAVE <proposal-digest>` confirmation and exclusively creates a mode-0600 proposal file. A proposal can contain local paths: keep it private. Nothing is activated by generating or saving. Rejected confirmation does not write. Without `--output`, the proposal/review is printed only.

For general wording, optionally use the **official Hermes model interface**:

```sh
hermes guardian propose 'YOUR INSTRUCTIONS' --model --output /absolute/operator/path/proposal.json
```

This explicitly sends the instructions and current Guardian policy (including configured paths) to the user's configured Hermes model/provider. Provider charges may apply; Guardian requires no separate paid key and never reads credentials. The model route uses `ctx.llm.complete_structured`, a strict JSON schema, a bounded timeout and local validation independent of optional host schema validation. It does not pick a provider or override credentials. Model availability/trust/network failure refuses generation; no silent fallback or activation. **No live provider completion has been tested in this credential-free environment.** Mocked protocol tests verify arguments, malformed results and failure handling; do not present those as real model inference.

Model output is untrusted. Every policy is checked by the live schema validator, restricted to the four recognized adapters, default block, existing protected paths and no removed/weakened path protections. Model-generated questions must be resolved by a new proposal; there is no switch to skip them. The model may still misunderstand prose. Review all rules and the locally generated gaps, even if it returns no questions. It cannot invent project paths, GitHub adapters or unsupported rule fields.

## Simulate without executing

Supply exact hypothetical calls in JSON, including independently chosen expected decisions:

```json
[
  {"name":"Git push gap", "tool":"terminal", "args":{"command":"git push origin main"}, "expected":"approve"}
]
```

```sh
hermes guardian simulate --proposal /absolute/operator/path/proposal.json \
  --home /absolute/active/hermes-home --cases /absolute/operator/path/cases.json
```

The example reports expected `approve`, actual `block`, reason `ambiguous_arguments`, and exits 1 for the mismatch. It never performs a Git operation. Cases are JSON data, not executable scripts. The same evaluator supplies the decision, reason and matched rule that enforcement uses. `block > approve > allow` remains unchanged.

Run seven reproducible regression templates with operator-supplied paths:

```sh
hermes guardian simulate --proposal /absolute/operator/path/proposal.json \
  --home /absolute/active/hermes-home \
  --workspace /absolute/disposable/workspace \
  --protected /absolute/configured/protected-root
```

The templates cover normal read, edit, deletion, GitHub push, compound shell syntax, protected read and protected deletion precedence. Their expected decisions are fixed; they are not copied from evaluator outputs. A stricter baseline or incorrect protected root can legitimately produce a mismatch. Investigate it rather than weakening protections just to obtain a pass. A cases file and template path arguments are mutually exclusive.

The pure simulator makes no tool calls, shell/process calls, network requests, audit writes, filesystem writes or approval prompts. It does inspect local path metadata/symlinks because the exact live evaluator does. Results are deterministic for the same policy, arguments, home and filesystem state. The enclosing Hermes CLI may perform normal host startup/logging; that is outside the pure simulator. For host-free simulation:

```sh
python3 -B guardian_lab.py simulate --policy /absolute/operator/path/policy.json \
  --home /absolute/intended/hermes-home --cases /absolute/operator/path/cases.json
python3 -B guardian_lab.py propose 'Ask before edits and deletions; block GitHub pushes.'
```

The standalone command uses Guardian defaults for proposals; it does not guess the active profile. `--policy` takes a raw policy, while `--proposal` takes the full proposal document. Use the Hermes command to generate/review against actual current settings. Simulation includes mandatory source/home/storage protections but cannot prove audit availability, final authorization, tool success, other host guards or later plugin argument rewriting. No execution or approval is implied by an `allow` or `approve` result.

## Review and activate as the operator

```sh
hermes guardian review /absolute/operator/path/proposal.json
hermes guardian activate /absolute/operator/path/proposal.json
```

Run in the intended Hermes profile with other config editors stopped. Review the entire proposed policy, questions, fixed limitations and tool-level changes. Weaker tool decisions are explicitly marked `weakens: true`; existing protected-path restrictions cannot be removed or weakened by this workflow. Stronger path restrictions are permitted. New protected roots must be configured deliberately through normal Hermes settings before proposing; the builder does not invent them.

Activation requires an interactive terminal and the exact `ACTIVATE <proposal-digest>` string; there is no `--yes`, agent tool or automatic activation path. The baseline digest must still match current effective settings. Guardian takes a nonblocking activation lock, durably saves an owner-only backup of the previous effective policy in sanctioned plugin storage, then calls public `ctx.set_config("policy", ...)`. Hermes atomically merges the settings update and preserves unrelated keys. Readback must match. The hook already rereads configuration on each call; no evaluator replacement is needed.

Invalid/stale policies, unanswered questions, denied confirmation, unsafe storage or backup failure do not change the current policy. A save/readback failure attempts to restore the previous effective policy and verifies it. If the underlying storage also prevents rollback, the command explicitly tells the operator to stop the agent and recover from the backup. No software can promise successful rollback on an unavailable filesystem. Other non-Guardian editors are not covered by the Guardian lock; do not race them with activation. A process crash after atomic replacement may leave the new policy active with its backup retained—inspect current settings after an interrupted activation.

Backups contain policy paths, not credentials or execution arguments. They are not the payload-free decision audit and should not be published. Recovery: inspect `policy-backup-*.json` in the active profile's `plugin-data/hermes-guardian` directory and use normal Hermes settings to restore its `policy` object. Activation does not enable a disabled plugin, turn off host YOLO, or override managed-config restrictions.

## Scope and deadline choices

Version 0.2.0 keeps the old configuration schema and hook/audit behavior. The original release is preserved on local branch `guardian-stable`. Automatic gap fuzzing/minimal-fix generation (P1) is deferred; this release supplies explicit fixed gap explanations and reproducible regression templates, not autonomous repair. No proposals or fixes are applied without operator approval.

See [VALIDATION.md](VALIDATION.md) for real test outcomes.
