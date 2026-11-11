# Real Hermes verification report

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

