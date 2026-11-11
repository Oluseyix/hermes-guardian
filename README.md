# Hermes Guardian

**0.2.0 — Policy Lab upgrade.** Describe → Generate → Simulate → Review → Activate → Enforce. The original validated release is preserved locally on `guardian-stable`; the deterministic enforcement and audit code remain unchanged. Start with the [Policy Lab operator guide](docs/POLICY_LAB.md) and [real 80-second product demo](examples/PRODUCT_DEMO.md).

```sh
hermes guardian propose 'Hermes can edit my coding projects, but must ask before deleting files or pushing code to GitHub.'
```

The command asks for clarification rather than inventing unsupported permissions. Choose the documented conservative offline template, or explicitly request the optional Hermes model builder with `--model`. All proposals are untrusted; simulation is read-only and activation requires operator confirmation. No separate API key or new dependency is required. The offline builder is deliberately limited, and the optional model route has not been live-provider-tested here.

A standalone Hermes Agent plugin for deterministic **allow / approve / block** tool policies. Built for the Nous Research Hermes Agent Plugin Hackathon, November 11, 2026 deadline.

Guardian checks configured local paths, rejects shell syntax it cannot interpret, and writes a redacted decision record before allowing a call to proceed. It uses the public `pre_tool_call` hook and Hermes's own approval gate. The enforcement hook has no model calls, third-party dependencies, network requests, subprocesses or core patches. Optional operator-side model generation is separate and explicitly requested.

**This is a policy hook, not a sandbox or complete security boundary.** Start with a local POSIX terminal/file backend, trusted plugins, and the default deny policy. Remote/container paths are not reliably comparable to the host filesystem. See [limitations](#limitations) before enabling.

## Quick demonstration

Python 3.11+ on macOS or Linux; Hermes and model credentials are not needed:

```sh
cd /path/to/hermes-guardian
PYTHONDONTWRITEBYTECODE=1 python3 verify.py
python3 demo.py --output /tmp/guardian-demo
```

The demo evaluates seven scenarios; it never executes the sample commands or writes the sample file contents. It demonstrates an ordinary read, a write requiring approval, protected reads/deletion, ambiguous shell syntax, an unknown executor, and audit self-protection. Only the redacted audit is written. Expected output: **1 allow, 1 approve, 5 block**. `approve` is a directive, not evidence that a human approved anything.

`verify.py` runs tests and the demo, then runs `hermes plugins validate /absolute/plugin/path --install-deps` when `hermes` is on PATH. Without Hermes, it explicitly reports a skip. Use `python3 verify.py --require-hermes` for a release check that fails if Hermes is absent.

## Install locally

Tested against the official Hermes **0.23.1** release on macOS/Python 3.14.9. Plugin Doctor and the full validator pass; seven real-runtime scenarios pass 194 checks, including real terminal approval prompts with scripted Once/Deny input and timeout. See [validation results](docs/VALIDATION.md) for commands, scanner cautions, and scope. The manifest accepts later releases, but they have not been tested.

First run the official checks on this trusted source:

```sh
hermes plugins validate /absolute/path/to/hermes-guardian --install-deps
hermes plugins doctor /absolute/path/to/hermes-guardian --ci
```

For local development, link this directory into the **active profile's Hermes home**. These commands do not overwrite an existing install; if using profiles, set `HERMES_HOME` to that profile's directory first:

```sh
cd /absolute/path/to/hermes-guardian
mkdir -p "${HERMES_HOME:-$HOME/.hermes}/plugins"
ln -s "$PWD" "${HERMES_HOME:-$HOME/.hermes}/plugins/hermes-guardian"
hermes plugins list
hermes plugins enable hermes-guardian
```

Restart the relevant Hermes process and confirm the plugin is enabled and loaded. A plugin that failed to load enforces nothing. The directory layout and `register(ctx)` entrypoint are native plugin APIs; this project is not a Hermes fork. After publication, installation by repository URL can use Hermes's normal installer; there is no published repository or catalog entry yet.

The native manifest declares `provides_hooks: [pre_tool_call]` at the top level. `capabilities: []` means no privileged override surfaces are requested. The catalog's nested `capabilities.provides_hooks` format is a different schema.

## Configuration

Put settings under `plugins.entries.hermes-guardian.settings.policy` in the active profile's `config.yaml`. Merge this fragment into existing configuration; do not replace the whole file. [examples/config.yaml](examples/config.yaml) is a complete settings fragment.

```yaml
plugins:
  entries:
    hermes-guardian:
      settings:
        policy:
          default_action: block
          rules:
            - {tool: read_file, action: allow}
            - {tool: write_file, action: approve}
            - {tool: patch, action: approve}
            - {tool: terminal, action: approve}
          protected_paths:
            - {path: "~/.ssh", action: block}
            - {path: "~/.aws", action: block}
            - {path: "~/.hermes", action: block}
            - {path: "/absolute/project/.env", action: block}
```

The last path is an example: replace it with your actual project secret file. The first three paths and four tool rules are the built-in defaults. There is **no global `.env` filename rule**: enumerate the files/directories you intend to protect. An explicitly empty `protected_paths` list removes user path rules, but not self-protection. The plugin source directory, its audit directory, and the active Hermes home inferred from the documented `plugin-data/<name>` layout remain blocked for recognized path-bearing calls.

Policy syntax is deliberately small:

| Field | Meaning |
|---|---|
| `default_action` | `allow`, `approve`, or `block` for tool names with no rule. Keep `block` for the intended MVP posture. |
| `rules` | List of exact `tool` names and `action` values. No patterns, regex, implicit case folding, or first-match overrides. |
| `protected_paths` | List of literal absolute paths (or trusted-config `~/` paths), with `block` or `approve`. Covers reads and writes. |

All three fields are required when providing a policy. Unknown keys, malformed types, unknown actions, or configuration-read failures block calls. Settings are read on every invocation through `ctx.get_config("policy", DEFAULT)`; schema warnings alone are not treated as validation. Up to 256 tool rules and 256 protected roots are accepted.

All matching rules participate; **block > approve > allow**. If there are no tool rules, `default_action` supplies the tool decision. A tool `allow` cannot override a protected-path block or ambiguous supported-tool arguments. Ties use configuration order only for the recorded reason. Evaluation is deterministic for the same configuration, arguments, and filesystem state; timestamps and audit IDs are intentionally not deterministic.

**Other tools:** you may explicitly allow or approve an exact external/MCP tool name, but Guardian then performs only a tool-name check. It does not infer the meaning of that tool's arguments. Allowing an arbitrary executor, browser, delegator, or file-access MCP tool can bypass path protection. This is why unknown tools, including `execute_code`, `delegate_task`, `search_files`, and process-management tools, default to block.

## Supported argument inspection

| Tool | Supported input |
|---|---|
| `read_file` | Absolute literal `path`; optional `offset`, `limit`. |
| `write_file` | Absolute literal `path`, `content`. Content is neither logged nor classified. |
| `patch` | Replace mode only: absolute `path`, `old_string`, `new_string`, optional `replace_all`, `mode: replace`. V4A/multifile patches and `cross_profile` are blocked. |
| `terminal` | The limited command grammar below; optional absolute `workdir`, `background: false`, integer `timeout` from 1 to 180. Other fields are blocked. |

Terminal grammar supports `pwd` without arguments; `cat`, `rm`, `touch`, `mkdir` with literal absolute operands; `cp` and `mv` with exactly two absolute operands. Options: `--`; `rm -r`, `-f`, `-rf`, `-fr`; `mkdir -p`. Quotes around ordinary path strings are accepted. There is no special handling for command aliases or executable paths such as `/bin/cat`.

Wrappers/interpreters (`sudo`, `env`, `sh`, Python, Node), pipelines, redirections, command chaining, substitutions, globs, expansions, backslashes, comments, control characters, unknown commands/options, relative paths, and background requests are blocked. Forbidden characters remain forbidden inside quotes. This intentionally rejects some harmless commands. It is a bounded grammar, **not a shell safety classifier**.

Path checks preserve both lexical identity and current symlink targets, handle `..` after symlink expansion, and reject resolution errors/loops. Equal paths, descendants, and ancestors of protected roots are guarded. Ancestor checks deliberately overblock: deleting a parent or copying into a containing directory must not avoid the rule. Future nonexistent leaf paths are supported. No protected file contents are opened by the evaluator.

## Approval semantics

Allow returns `None`: Hermes and other guards may still refuse the call. Block returns `{"action": "block", "message": ...}`. Approval returns `{"action": "approve", "message": ..., "rule_key": ...}` and lets Hermes handle the response, timeout, and execution. Guardian never prompts itself and never marks a call approved.

Every approval directive gets a fresh invocation key. A prior session/Always approval for Guardian's previous key cannot authorize a changed payload, or even a repeated call. Select **Once** in the host prompt to avoid accumulating useless permanent entries. Host policy can still bypass the prompt: **YOLO, approvals-off, and configured unattended/cron/single-query approval modes may auto-approve**. For non-negotiable protected actions, use `block`. Check the host's approval settings and disable those bypass modes when a human decision is required.

Messages deliberately omit raw arguments and paths. Inspect the original Hermes tool call before approving; the generic Guardian reason alone is insufficient for informed approval. The plugin does not implement an approval UI.

## Audit and operations

Each evaluated call attempts to append a `policy_decision` JSON record to:

```text
<active Hermes home>/plugin-data/hermes-guardian/audit.jsonl
```

Records contain UTC time, random event ID, selected action, fixed reason code, positional rule reference (`tool:0`, `path:0`, etc.), and a recognized tool name. Other tool names are redacted. Arguments, task IDs, command text, file paths/content, results, exception messages, and hashes of secret-bearing input are **never persisted**. This is redaction by omission, not a promise that a secret-detection regex catches everything. Rule positions refer to the configuration at evaluation time; keep operator-managed config history if you need historical reconstruction.

The file is owner-only (`0600`), appended under an OS file lock, and synced before proceeding. New directories created by Guardian use `0700`; Hermes may have already created its data directory with different permissions. Final-component symlinks, nonregular files, and hard-linked audit files are refused. There is no telemetry or automatic upload.

Storage errors, lock contention, a partial trailing record, and the **16 MiB capacity limit** block the current call, including one otherwise allowed. Lock acquisition is nonblocking to avoid hanging a host hook; concurrent callers may need to retry. Nothing is silently deleted or rotated. Stop Hermes, archive the audit outside the active data directory, repair any partial record, and restart. Disk exhaustion means a failure cannot itself be reliably logged. A record written just before a sync failure can contain the evaluated policy action even though the final directive blocked.

These are **decision records, not proof of execution or final human authorization**. Another hook may veto, Hermes may auto-approve, or execution may fail after the record. There is no post-execution logging or tamper-evident chain. The owning OS user can alter the file.

To recover from an invalid policy or intentional default-deny blockage, edit the settings using your own terminal or Hermes configuration UI. To stop enforcing, run `hermes plugins disable hermes-guardian` as the operator and restart the host. Uninstall/update do not remove the sanctioned plugin data directory; archive/delete it yourself when desired.

## Limitations

- Only calls reaching Hermes's public hook are inspected. Direct Python calls, host/plugin code, previously launched processes, and activity outside the agent are not mediated.
- No OS isolation, malicious-plugin resistance, prompt-injection detector, network firewall, recipient authorization, or full interpreter analysis. Trusted executable lookup, shell startup files/functions, and an uncompromised host are assumptions.
- Path checks use the plugin host's POSIX filesystem. Use a local backend with the same path namespace. Container/SSH/remote filesystems, Windows paths, hard-link aliases, case-insensitive aliases, mount aliases, and symlink races between inspection and execution are not secured.
- The hook receives original arguments. Other hooks can mutate arguments after inspection; do not combine Guardian with argument-rewriting plugins for protected workflows. A hard block remains a veto, but an allowed call is not rechecked by Guardian after rewrites.
- A load/discovery failure or disabled plugin removes protection. Hermes 0.23.1 returns a block for failing/timed-out `pre_tool_call` callbacks; Guardian also catches its own ordinary exceptions to return fixed, redacted errors. It cannot protect against process termination, broader host failure, or hook bypass.
- File-tool side effects, including Hermes's syntax checks after a patch, remain host behavior. Terminal timeout promotion/background behavior can depend on host configuration. The plugin does not sandbox those effects.
- Restrictive defaults are intentionally inconvenient. This MVP does not support arbitrary development commands or automatic policy discovery. Broaden exact tool permissions only after reviewing the tool's reach.
- macOS/Linux only (`fcntl`, POSIX descriptors). Unit tests passed on macOS Python 3.13.7 and 3.14.9; host integration passed on Hermes 0.23.1/Python 3.14.9. Linux, Desktop/TUI/gateway interfaces, remote backends, and model-driven end-to-end conversations were not tested. PTY prompt answers were scripted, not supplied by a human tester.

## Differentiation and disclosure

The catalog already has security and permission plugins; [the comparison](docs/API_FINDINGS.md#catalog-comparison) records the closest overlaps, including the live catalog reviewed on November 10. Guardian's distinction is its small in-process, dependency-free policy engine, native approval directives, strict local-path/command scope, and payload-free audits. Archytan Lite and Tenuo already provide argument-level authorization; Policy Backtester already combines policies with native approval. Guardian is an independently written alternative with a smaller deployment footprint, not a novel security category or a replacement for those systems.

Enforcement reads: plugin settings through Hermes, and path metadata/symlink targets needed for policy checks (possibly outside the plugin directory). Enforcement writes: its own persistent audit. The enforcement hook performs no credential-file reads, shell execution, model calls, external network calls, background work, telemetry, or self-update. The optional operator command `hermes guardian propose --model` sends instructions and policy paths through the public Hermes model interface; the provider may charge. Confirmed operator activation writes settings through the public host API and stores owner-only policy backups. Tests and verification scripts are developer-only and may run Python subprocesses or invoke the installed Hermes validator; they are not imported by the plugin.

MIT licensed. A [catalog draft](submission/hermes-guardian.yaml.in) is prepared with explicit unpublished metadata placeholders. No repository, pull request, catalog submission, or site has been published by this build.

## Release preparation

The [80-second product demo](examples/PRODUCT_DEMO.md) exercises real Hermes 0.23.1 dispatch and native approval using disposable fixtures. See the [release review](docs/RELEASE_REVIEW.md) and [publication checklist](submission/RELEASE.md) for verified results, missing metadata and approval-gated publication commands. Nothing has been published or submitted.
