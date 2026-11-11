# Verification — Guardian 0.2.0 Policy Lab upgrade

Verified November 11, 2026, on macOS arm64 with official Hermes **0.23.1**, commit `3b421578588243f920886e6fe79a6faa87ea026e`. User-supplied deadline: November 11 at 5 PM EST (22:00 UTC / 23:00 Lagos). No external publication or submission occurred.

## Preservation and scope

Before changing any project file, initialized local Git and committed the complete previously reviewed tree on **`guardian-stable`**, commit **`afa7733d17f2beed0d1ab6e5bd7faca4a8f1a2c2`**, then created `guardian-upgrade`. The baseline uses a neutral local snapshot author; no public maintainer identity was inferred. Original `guardian/policy.py`, `guardian/runtime.py` and `guardian/audit.py` remain byte-for-byte unchanged. The entrypoint additionally registers the operator CLI; version is 0.2.0 and the configuration schema is unchanged.

## Upgrade results

| Verification | Actual outcome |
|---|---|
| Python 3.13.7 unit suite | **87 passed**, including the original 63 tests |
| Installed Hermes Python 3.14.9 unit suite | **87 passed** |
| Original real-runtime matrix | **7 scenarios / 194 checks passed again** |
| New real-host product integration | **31 checks passed** |
| Original non-executing demo | **7 scenarios passed** |
| Product demo rehearsal | **80.00 seconds**, actual host outputs, scripted PTY responses; exit 0 |
| Plugin Doctor | **Exit 0**, actual load, zero tools / one hook |
| Full `plugins validate --install-deps` | **Exit 0**, same reviewed five scanner locations; no new runtime/private-API warning |
| Current official catalog parser | Draft metadata placeholders rejected as expected; in-memory schema fixture accepted and manifest fields matched |

The 24 new unit tests cover exact-evaluator simulation, no file-content access/writes, process/network/approval refusal guards, symlinks/self-protection, precedence, visible expectation mismatches, malformed cases/policies/model outputs, unknown/ambiguous wording, strict known-tool/path constraints, unchanged stronger rules, stale proposals, provider-error redaction, explicit/rejected confirmation, backup failure, owner-only backups, symlink storage refusal, lock contention, successful rollback after injected post-write/readback failures, and explicit recovery errors when rollback itself cannot write.

New real-host checks use actual plugin discovery, the installed `hermes guardian` CLI, public `ctx.get_config` / `ctx.set_config`, host configuration serialization and real tool dispatch. They verify settings-over-legacy precedence, legacy fallback, unrelated-key preservation, rejected and confirmed proposal saves, rejected and confirmed activation, effective-policy backups, all seven Lab/live policy decision/reason/rule matches, unattended denial of approval requests, protected fixture preservation and live enforcement of a changed policy without replacing the hook. For approval cases, Lab predicts **approve** while the unattended host refuses execution; comparing audit policy decisions avoids conflating those two layers.

The product demonstration uses the honest **offline exact-language template**, not a model. It accepts the original natural-language example, asks clarification about unsupported scope/Git behavior, accepts the explicit conservative wording, simulates seven cases, reviews and confirms the digest, saves through Hermes, then performs an actual allowed read, native Once-approved write and protected block. The real audit is displayed. Rehearsal inputs are scripted; a human video remains outstanding.

## Commands executed for the upgrade

Use the same isolated environment from the historical installation report below. `IG`, `HS` and `HP` denote private integration storage, official source and installed Hermes Python; substitute your own paths. Commands ran from this repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -q
python3 "$IG/run.py" "$HP" -m unittest discover -s tests -q
python3 "$IG/run.py" "$HP" tests/run_hermes_matrix.py --source "$HS" --workspace "$IG/upgrade-cases"
python3 "$IG/run.py" "$HP" tests/product_integration.py --source "$HS"
python3 "$IG/run.py" "$HP" tests/rehearse_product_demo.py --source "$HS" --log "$IG/logs/product-demo.log"
PYTHONDONTWRITEBYTECODE=1 python3 demo.py --output "$IG/upgrade-standalone-demo"
python3 "$IG/run.py" "$HS/.hermes/bin/hermes" plugins doctor "$PWD" --ci
python3 "$IG/run.py" "$HS/.hermes/bin/hermes" plugins validate "$PWD" --install-deps
git diff guardian-stable -- guardian/policy.py guardian/runtime.py guardian/audit.py
git diff --check
```

All completed checks above exited 0. Matrix logs are in `upgrade-cases/matrix-logs`; other private evidence: `logs/product-integration.log`, `logs/product-demo.log`, `logs/product-demo-runner.log`, `logs/upgrade-doctor.log`, `logs/upgrade-validate.log`. Do not publish raw fixture/audit/config logs. The developer harness uses the installed venv's official `hermes` console entrypoint for subprocess CLI checks, so a fresh fixture HERMES_HOME does not need separate PM installation state.

## Failures and limitations

- Initial new CLI integration failed because the PM launcher had no committed dependency environment under the disposable Hermes home. Using the already-installed official virtualenv console entrypoint fixed this test setup issue; no core patch or global configuration change.
- Rejected saves/activation, malformed outputs, missing confirmation, stale policies and injected storage failures are intentional negative tests, not successful activations. A persistent storage outage can prevent rollback; the tested error explicitly says to stop the agent and recover the retained backup. An interrupted process after replacement may leave the approved new policy active. Concurrent non-Guardian config editors must be stopped.
- The optional `ctx.llm.complete_structured` route is source/API verified and unit-tested with controlled responses, **not live-provider-tested**. No model completion or credentials were fabricated. A configured provider is required for optional model inference, and may charge; no separate key is mandatory. The safe offline workflow is complete and tested.
- The builder cannot implement project-scoped positive access or Git push approval with the unchanged evaluator. It asks clarification, preserves path protections, blocks unsupported Git operations and exposes tool-wide limitations. It does not guess paths or tool capabilities.
- P1 automatic edge-case generation/minimal-fix suggestions are deferred. Seven fixed hypothetical regressions and explicit gaps are provided; no autonomous repairs.
- Existing limitations remain: not a sandbox; local path races/aliases, host auto-approval, later argument rewrites, unsupported tool adapters and disabled/failed loading limit coverage. Lab predicts policy only, not audit availability, execution success or final consent.
- Linux/remote CI, provider inference, full model-driven chat and gateway/Desktop/TUI remain unverified. No public repository, catalog PR, hackathon form or human-recorded final video exists yet. See [release checklist](../submission/RELEASE.md).

The five scanner locations remain the protected AWS/SSH path literals in `policy.py` and `examples/config.yaml`, plus the destructive disposable-command example in `examples/LIVE_DEMO.md`; detailed review remains below. No scan was suppressed. Host isolation is still not a sandbox.

---

# Original 0.1.0 verification (historical)

Verified November 10, 2026, on macOS Apple Silicon. This report supersedes the earlier source-only verification.

## Result

- **Official Hermes 0.23.1 installed and exercised**, commit `3b421578588243f920886e6fe79a6faa87ea026e`, Python **3.14.9**.
- **Plugin Doctor: PASS**, exit 0. Real discovery, parsing, import and registration: 0 tools, 1 hook.
- **Full catalog validator with `--install-deps`: PASS**, exit 0, with reviewed scanner cautions below.
- **63 unit tests: PASS** on both Python 3.13.7 and the installed Hermes Python 3.14.9.
- **7 real-runtime scenarios / 194 checks: PASS**, including real terminal prompts with scripted Once/Deny answers and an unanswered timeout.
- **100 concurrency regression runs / 8,000 append attempts: PASS** after the audit-creation fix. Contended calls intentionally fail closed; this does not mean all attempts wrote a record.
- **7 non-executing demo scenarios: PASS**.
- No core source patches, provider credentials, model calls, Git pushes, PRs, catalog submission, or hackathon-form submission.

Machine-readable results: [verification-results.json](verification-results.json). The tests invoke real Hermes loading and `model_tools.handle_function_call`; they do not mock its dispatcher, hooks, file handlers, or approval gate. These harness imports are development-only, not plugin runtime dependencies.

## Isolation and installation

Followed the [official source installation instructions](https://hermes-agent.nousresearch.com/docs/getting-started/installation). Inspected the downloaded installer before running it. Used its `venv` and `python-deps` stages, which delegate dependency preparation to official PM with locked dependencies. Browser/computer-use downloads were excluded. The final products/setup stages, which would expose commands and edit shell startup files, were not run.

Retained environment:

| Item | Location |
|---|---|
| Official release checkout | `/absolute/path/to/hermes-source` |
| Isolated test storage | `/absolute/path/to/integration` |
| Test configuration | `hermes-guardian-integration/home/config.yaml` |
| Environment launcher | `hermes-guardian-integration/run.py` |
| Private official Hermes launcher | `/absolute/path/to/hermes-source/.hermes/bin/hermes` |
| Logs | `hermes-guardian-integration/logs/` and `cases/matrix-logs/` |

The launcher preserves ordinary OS context but strips inherited API/provider credentials and sets private Hermes, tool-store, Python-install, cache, and data roots. It prepends the private Hermes launcher only to child-process PATH. Test config sets `cli.expose_on_path: false`. Every integration scenario uses a new temporary Hermes home and disposable fixtures.

The normal `~/.hermes` and `~/.local/bin/hermes` were still absent after installation. No existing user configuration or credentials were overwritten; no system-wide setup was performed. Official source `git status --short` was clean. The checkout intentionally includes the runtime packages and locale assets, not Desktop/TUI frontend builds.

## Commands executed

Personal paths and generated environment identifiers are sanitized below. Set these aliases to your isolated installation before reproducing the commands:

```sh
IG=/absolute/path/to/integration
HS=/absolute/path/to/hermes-source
GP=/absolute/path/to/hermes-guardian
HP="$IG/home/installs/<install-id>/environments/<environment-id>/venv/bin/python"
```

Source and official bootstrap:

```sh
curl -fsSL https://hermes-agent.nousresearch.com/install.sh -o /private/tmp/hermes-guardian-install.sh
git -C "$HS" fetch --depth 1 origin tag v0.23.1
git -C "$HS" checkout v0.23.1
git -C "$HS" sparse-checkout set agent tools hermes_cli gateway tui_gateway cron acp_adapter plugins providers hermes_platform hermes_agent pm scripts plugin-catalog --skip-checks
git -C "$HS" sparse-checkout add locales

python3 "$IG/run.py" bash /private/tmp/hermes-guardian-install.sh --dir "$HS" --stage venv --non-interactive --skip-browser --skip-computer-use --verbose
python3 "$IG/run.py" bash /private/tmp/hermes-guardian-install.sh --dir "$HS" --stage python-deps --non-interactive --skip-browser --skip-computer-use --verbose
python3 "$IG/run.py" "$HS/.hermes/bin/hermes" --version
```

Network downloads required approved execution outside the tool sandbox after sandbox DNS failures. They succeeded. A sandboxed `--version` invocation warned that its optional latest-stable lookup could not resolve the host, but correctly reported the local 0.23.1 version, revision, and Python runtime.

Required official commands, both exit 0:

```sh
python3 "$IG/run.py" "$HS/.hermes/bin/hermes" plugins doctor "$GP" --ci
python3 "$IG/run.py" "$HS/.hermes/bin/hermes" plugins validate "$GP" --install-deps
```

Final checks, all exit 0:

```sh
cd "$GP"
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -q
python3 "$IG/run.py" "$HP" verify.py --require-hermes
python3 "$IG/run.py" "$HP" tests/run_hermes_matrix.py --source "$HS" --workspace "$IG/cases"
```

The second command runs the 63 tests under Hermes's interpreter, the seven demo scenarios, and the complete official validator. Its final log is `logs/verify-final.log`; Doctor's final log is `logs/doctor-final.log`. The stress check repeated `test_audit.AuditTests("test_concurrent_records_not_interleaved")` 100 times in a standard unittest suite under the Hermes interpreter.

Live catalog:

```sh
curl -fsSL https://hermes-agent.nousresearch.com/docs/api/plugin-catalog.json -o "$IG/live-catalog.json"
```

The retained environment is for reproduction. It is not installed on normal PATH. The exact generation path may change after a future PM update; find the selected environment in `home/installs/<install-id>/facts.json`. The environment launcher is local infrastructure, not part of the plugin's installation requirements.

## Actual runtime matrix

| Context | Checks | Observed approval behavior |
|---|---:|---|
| No interactive user/gateway | 28 | Write refused promptly; destination absent. |
| Cron, `cron_mode: deny` | 28 | Write refused promptly; destination absent. |
| Single query, `single_query_mode: deny` | 28 | Write refused promptly; destination absent. |
| `approvals.mode: off` | 28 | Approval-required fixture write executed without a prompt. Protected-path blocks still held. |
| Interactive PTY, scripted `o` | 27 | Real English host prompt displayed; Once allowed exactly the fixture write. |
| Interactive PTY, scripted `d` | 27 | Real host prompt displayed; Deny left the destination absent. |
| Interactive PTY, no response | 28 | Host timed out at approximately 3.09 seconds and blocked; destination absent. |
| **Total** | **194** | **All passed.** |

Each scenario also checked actual allowed file reads and terminal `cat`, protected read/write/deletion, symlink aliases and loops, traversal, relative paths, compound/substitution/glob/wrapper rejection, alternate patch mode, audit self-protection, audit-lock failure and recovery, invalid live settings and repair, owner-only audit permissions, and omission of fixture secrets/paths/task IDs from audit records.

The fixture-only harness writes its own settings and files. It does not run a model or weaken a production profile. The approvals-off test deliberately demonstrates the host's documented bypass in an isolated profile; it is not a recommended deployment setting. These are real prompt and dispatcher tests with **scripted terminal input**, not a human usability test or a full model-driven conversation. We did not test gateway, Desktop or TUI approval UI, or a full cron scheduler invocation; cron/single-query tests use the real host context markers and gate.

## Failures found and resolved

1. **Sparse checkout lacked locale assets.** The first PTY run displayed translation keys, though Once still worked. Added official `locales/` and reran all prompt cases. No core or plugin behavior was patched.
2. **Harness assumed repeated reads always returned contents.** Hermes's file tool returns an unchanged stub, then refuses repeated identical reads. Recovery tests now accept the first unchanged result and use a fresh fixture after configuration repair. This was a test assumption, not a Guardian defect.
3. **Intermittent concurrent audit creation failure.** The final full run exposed `FileNotFoundError` from concurrent non-exclusive `O_CREAT` opens. Stress reproduced it in 14/30 sandbox runs and 15/30 runs outside the sandbox. Guardian already blocked those calls, but availability was unnecessarily reduced. Changed `guardian/audit.py` to open existing files first, elect the first creator with `O_CREAT | O_EXCL`, and on `EEXIST` open the winner without creating. No-follow, ownership/link checks, nonblocking flock, append, sync, and fail-closed deletion behavior remain. Added exclusive-create, losing-creator, bounded-deletion-race and cross-process regressions. All 100 post-fix stress runs passed.
4. **Initial API note overstated exception skipping.** Inspected release source confirms 0.23.1 blocks failing/timed-out `pre_tool_call` callbacks. Corrected documentation and an explanatory comment; Guardian retains its own fixed-message exception boundary.

No manifest, dependency, capability-declaration, private-API, or core-override failure required a workaround. No security-scanner failure was suppressed.

## Scanner cautions reviewed

The complete validator passes with **caution**, not a clean/unqualified scan:

| Finding | Reported locations | Review |
|---|---|---|
| `aws_dir_access` | `config.yaml:15`, `policy.py:25` | Protected-path configuration/default literals. Runtime checks path metadata; it does not read AWS credential contents. |
| `ssh_dir_access` | `config.yaml:14`, `policy.py:24` | Protected-path configuration/default literals; same metadata-only behavior. |
| `destructive_root_rm` | `LIVE_DEMO.md:14` | A documented destructive command targeting an explicitly disposable protected fixture. Guardian must veto it; the document is not executable runtime code. |

The abbreviated `config.yaml` refers to `examples/config.yaml`. Findings are retained for reviewer inspection rather than removed to make a scanner green. The validator also correctly reports host isolation: **runs in the plugin host**, not a sandbox.

## Remaining risks and submission status

- Tested only on macOS Apple Silicon; Linux/other Python CI jobs have not run remotely.
- No model-driven chat, Desktop/TUI/gateway UI, actual cron scheduler, or remote/container backend verification.
- YOLO and alternate unattended `approve` settings remain source-reviewed behavior; only approvals-off was exercised as an automatic-approval bypass.
- Original-argument hooks cannot secure later rewrites; paths remain subject to races and hard-link/case/mount aliases. Explicitly allowed unrecognized tools get only name checks.
- Audit is a local decision log, not proof of execution, human authorization, or tamper resistance. Storage failure/lock contention/capacity deliberately refuse calls.
- Disabled/unloaded Guardian provides no enforcement. It is not an OS sandbox.
- Catalog overlap is substantial; [API_FINDINGS.md](API_FINDINGS.md#catalog-comparison) gives the refreshed comparison and a limited differentiation claim.
- [Catalog entry draft](../submission/hermes-guardian.yaml.in) is prepared, but repository URL, owner-approved maintainer, and exact release SHA are intentionally placeholders. The supplied project directory has no Git metadata yet; no commit or public URL is invented.
- Before publication, obtain owner approval, create/pin the exact release tree and rerun full validation against that tree. Do not represent this draft as catalog-listed or submission-complete.

