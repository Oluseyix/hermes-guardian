# API findings and scope

Inspected November 10, 2026, before implementation. Official source checkout:
[`c382971c9fd649938937422ad937a3954a9f1128`](https://github.com/NousResearch/hermes-agent/tree/c382971c9fd649938937422ad937a3954a9f1128).
Current released version checked through GitHub's official release API:
[v0.23.1](https://github.com/NousResearch/hermes-agent/releases/tag/v0.23.1), release target `3b421578588243f920886e6fe79a6faa87ea026e`.
The initial main revision is distinct from the release target. Follow-up verification installed and tested the official **v0.23.1 release target** in isolated storage: Doctor, full validator, real tool dispatch, and terminal approval checks passed. See [VALIDATION.md](VALIDATION.md). This verifies that release on the tested platform, not every later release.

Primary documentation: [Build a Hermes Plugin](https://hermes-agent.nousresearch.com/docs/developer-guide/plugins), [Catalog submission](https://hermes-agent.nousresearch.com/docs/developer-guide/plugins/catalog-submission).

## Verified contracts

| Surface | Source finding | Guardian use |
|---|---|---|
| Entry point | Directory `plugin.yaml` plus `__init__.py` exposing `register(ctx)`; namespaced package import. | Relative package imports, one registered hook. |
| Hook | `ctx.register_hook("pre_tool_call", callback)`; callback receives `tool_name`, `args`, `task_id`, and additional keyword metadata. | `pre_tool_call(self, tool_name, args, task_id="", **kwargs)`. |
| Allow | No directive means proceed to other host checks. | Returns `None`; never claims to force execution. |
| Block | `{"action": "block", "message": nonempty_string}` is a veto. | Fixed reason message with no raw payload. |
| Approve | `{"action": "approve", "message": ..., "rule_key": ...}` routes to `request_tool_approval`. | Fresh invocation key; no custom prompt or cached authorization. |
| Precedence | Host scans for blocks before choosing its first valid approval. | Internal rules also use block > approve > allow. |
| Exceptions | Verified v0.23.1 `PluginDispatchMixin._run_hook_callbacks` converts ordinary callback exceptions/SystemExit and timeouts for `pre_tool_call` to blocks. Broader executor failure/hook suppression remains outside plugin control. | Catch internal exceptions for fixed redacted errors; avoid blocking lock waits. This corrects the initial broader claim that crashed callbacks are simply skipped. |
| Config | `ctx.get_config(key, default)` reads plugin-relative `plugins.entries.<id>.settings`; legacy `config` fallback exists. Manifest schema mismatch warnings do not stop loading. | Strict policy validation inside the hook on every call. |
| Storage | `plugins.plugin_storage.plugin_data_dir(name)` resolves active Hermes home on each call and creates `plugin-data/<name>`. | Resolve per invocation, write audit outside install tree. |
| Capabilities | Native `provides_tools`/`provides_hooks` are top-level. Native `capabilities` is a list of privileged capability IDs, not the catalog mapping. | `provides_hooks: [pre_tool_call]`, `capabilities: []`, no tools. |
| Local installation | User directory discovery under the active home's `plugins/`; plugins must be enabled. | Document local source symlink and explicit enable. |
| Validation | `hermes plugins validate PATH --install-deps`; `hermes plugins doctor PATH --ci` performs actual discovery/loading. | Verification script invokes validation when installed; reports absence explicitly. |

Relevant pinned source:

- [Plugin context](https://github.com/NousResearch/hermes-agent/blob/c382971c9fd649938937422ad937a3954a9f1128/hermes_cli/plugins_context.py): `get_config`, `register_hook`.
- [Directive dispatch](https://github.com/NousResearch/hermes-agent/blob/c382971c9fd649938937422ad937a3954a9f1128/hermes_cli/plugins.py): `_get_pre_tool_call_directive_details`, `_resolve_block_from_details`, `_dispatch_pre_tool_call_hooks`.
- [Hook dispatch](https://github.com/NousResearch/hermes-agent/blob/c382971c9fd649938937422ad937a3954a9f1128/hermes_cli/plugins_dispatch.py): callback failure/timeout behavior.
- [Approval gate](https://github.com/NousResearch/hermes-agent/blob/c382971c9fd649938937422ad937a3954a9f1128/tools/approval.py): `_run_approval_gate`, `request_tool_approval`.
- [Storage](https://github.com/NousResearch/hermes-agent/blob/c382971c9fd649938937422ad937a3954a9f1128/plugins/plugin_storage.py), [manifest parser](https://github.com/NousResearch/hermes-agent/blob/c382971c9fd649938937422ad937a3954a9f1128/hermes_cli/plugins_manifest.py), [validator](https://github.com/NousResearch/hermes-agent/blob/c382971c9fd649938937422ad937a3954a9f1128/hermes_cli/plugin_validate.py).
- [File tools](https://github.com/NousResearch/hermes-agent/blob/c382971c9fd649938937422ad937a3954a9f1128/tools/file_tools.py): `read_file`, `write_file`, `patch` take `path`. Patch handler also accepts V4A mode even when not advertised in the model-facing schema; Guardian blocks that mode.
- [Terminal](https://github.com/NousResearch/hermes-agent/blob/c382971c9fd649938937422ad937a3954a9f1128/tools/terminal_tool.py): command schema uses `command` and `workdir`; extra PTY/background lifecycle arguments exist but are outside this MVP.

These internal source functions were inspected and used by optional development checks; **the runtime plugin does not import or patch them**. Its only direct Hermes import is the documented storage helper.

## Approval and composition limits

Gate failure/denial blocks, and a no-human context normally fails closed. However, host YOLO, `approvals.mode: off`, saved approvals, and configured unattended modes affect the gate. Guardian does not reinterpret or bypass those settings. Per-invocation keys prevent reuse of its prior saved keys, but not host-wide automatic approval. Protected rules default to block for that reason.

The dispatcher collects optional `modify` results and shallow-merges arguments after callbacks have inspected the original call. Guardian cannot prove that another plugin's final arguments match what it checked. Use trusted plugins without argument rewriting for protected workflows. This limitation is explicitly documented rather than worked around by patching the executor.

## Catalog comparison

Reviewed the pinned catalog, including entries declaring `pre_tool_call` and permission/security terms. The table is based on catalog disclosures, not an independent audit of each plugin's implementation. It is not an exhaustive uniqueness claim.

**Live refresh:** fetched the [official published catalog](https://hermes-agent.nousresearch.com/docs/api/plugin-catalog.json), generated `2026-11-10T18:50:48.589621+00:00`, containing **1,578 entries**. Snapshot SHA-256: `3437c7086d955844bebe8bb39c308a9a438b9edabe851590319d1e0b62c2d21c`. No entry named `hermes-guardian` appeared in this snapshot. Clearance had advanced to 1.1.0 (`2dffa6193ac5eb72f0e5aeb412ba3d68ebaf47e8`), with gateway-admin tier mapping; its role-based scope still differs.

Additional close overlaps found in the live review:

| Plugin and catalog pin | Existing behavior | Material distinction / overlap |
|---|---|---|
| [Archytan Lite](https://github.com/High-ArchyTech-Solutions/hermes-archytan-lite/tree/38748165b089f776acf9d6119eaeafdb76eed83e) 0.1.0 | Path/program/resource authorization, ambiguous-command refusal, signed one-use permissions and receipts from a separate proprietary Docker gate. | Closest command/path overlap. Guardian uses a small in-process stdlib evaluator and Hermes approvals, without a service, signing key or container. Guardian lacks signed receipts and an external trust boundary. |
| [Policy Backtester](https://github.com/noviceadam666/policy-backtester/tree/2fdaade2a2e34a01b611fd074d8deb8d9853c7be) 0.5.2 | Replay historical tool calls, shadow promotion, enforce with block/native approve; stores command arguments. | Policies and native approval already exist. Guardian avoids historical databases/promotion machinery and omits all argument payloads from its audit. |
| [Tracekit](https://github.com/Cygnux-Labs/Tracekit/tree/d41c68e335a0986100b8747729659798bcf9d949) 0.1.0 | Local/remote signer decides calls and records signed runs; arguments/results leave the hook for the signer. | Guardian has no service or payload transfer and no cryptographic attestation. |
| [withHuman](https://github.com/withHumanAI/withHuman/tree/3fcc9dd3787e4941aaf4657e808c78c3f98d49a9) 1.5.4 | Team approval through a hosted organization and downloaded CLI. | Guardian uses the host's native gate entirely locally, with no team workflow or hosted integration. |
| [Scamgate](https://github.com/odaiameera/scamgate/tree/041ec7bf6f73bf3e1609ca914bcbfe01fc3cf393) 0.3.3 | Link/payment guard with phishing feeds and protection of guard/control files. | Self-protection is not unique. Guardian has no threat feeds or destination classification and respects host auto-approval for `approve` rules. |

**Assessment:** Guardian materially differs in architecture, deployment requirements, and audit-data minimization, but its central policy/path-check/approval concepts are already represented. It is not a fork of these plugins. Present it as a focused local policy implementation with demonstrated reliability, not the first Hermes security plugin. Catalog admission and hackathon judging remain maintainer decisions.

| Existing plugin | Catalog scope | Guardian's narrower distinction |
|---|---|---|
| [Tenuo](https://github.com/NousResearch/hermes-agent/blob/c382971c9fd649938937422ad937a3954a9f1128/plugin-catalog/hermes-tenuo.yaml) | Signed expiring warrants, argument constraints, scoped authorization; audit includes arguments, optional control-plane streaming. | No warrants, SDK/native dependency, or control plane; raw payloads omitted from audits. Tenuo already occupies argument-level authorization. |
| [Clearance](https://github.com/NousResearch/hermes-agent/blob/c382971c9fd649938937422ad937a3954a9f1128/plugin-catalog/clearance.yaml) | Sender tiers and per-user tool permissions on messaging/webhook surfaces. | Local path and command argument checks; no identity/role administration. |
| [Command Reviewer](https://github.com/NousResearch/hermes-agent/blob/c382971c9fd649938937422ad937a3954a9f1128/plugin-catalog/command-reviewer.yaml) | Deterministic rules plus model review of commands/scripts; shadow default, approval precedents. | No script-content reads or model classification; unsupported commands block instead of being reviewed. |
| [CaMeL Guard](https://github.com/NousResearch/hermes-agent/blob/c382971c9fd649938937422ad937a3954a9f1128/plugin-catalog/camel-guard.yaml) | Trusted user capabilities and untrusted-output state; disclosed coarse argument coverage. | Explicit path checks and deterministic rules with no intent classification. |
| [Egress Guard](https://github.com/NousResearch/hermes-agent/blob/c382971c9fd649938937422ad937a3954a9f1128/plugin-catalog/egress-guard.yaml) | Credential redaction, outbound upload approvals, statistical output disclosure controls. | No argument/output rewriting or destination analysis; focuses on protected local actions. |
| [Gatekeeper](https://github.com/NousResearch/hermes-agent/blob/c382971c9fd649938937422ad937a3954a9f1128/plugin-catalog/hermes-gatekeeper.yaml) | Deterministic outbound-message consent/suppression/quiet-hour rules. | Local filesystem policy; no recipients or messaging consent model. |
| [Security](https://github.com/NousResearch/hermes-agent/blob/c382971c9fd649938937422ad937a3954a9f1128/plugin-catalog/hermes-security.yaml) / [Plugin Guard](https://github.com/NousResearch/hermes-agent/blob/c382971c9fd649938937422ad937a3954a9f1128/plugin-catalog/hermes-plugin-guard.yaml) | Repository security review / static candidate-plugin review. | Enforcement at tool invocation rather than a code review workflow. |

Implementation plan followed: independent native adapter; strict rule engine; conservative shell/path inspection; redacted durable audit; adversarial unit tests; non-executing demonstrations; source-only upstream checks; explicit separation from full host validation.

## Before catalog submission

The complete official validator and real allow/deny/timeout terminal flows now pass; scanner cautions are reviewed in VALIDATION.md. Before submission, revalidate the exact committed release tree, obtain the owner's publication approval, and replace the catalog draft's metadata placeholders with a public repository URL and full 40-character release commit pin. None is fabricated here. No PR, upload, or public publication was performed.

## 0.2.0 operator workflow API verification (November 11, 2026)

Inspected the installed official 0.23.1 `plugins_context.py`, `plugins_state.py` and `agent/plugin_llm.py` before implementing the upgrade. Public `ctx.register_cli_command(name, help, setup_fn, handler_fn)` registers `hermes guardian`; no tool or slash-command activation surface is added. Native manifest/catalog tool and hook declarations remain unchanged; there is no invented CLI capability field.

Public `ctx.llm.complete_structured(instructions=..., input=..., json_schema=..., schema_name=..., purpose=..., temperature=..., max_tokens=..., timeout=...)` returns `result.parsed`. The optional builder uses that surface without provider/model/auth overrides, and validates the parsed value locally. See [official LLM access](https://hermes-agent.nousresearch.com/docs/developer-guide/plugin-llm-access). Provider inference is not part of enforcement or simulation, and was not live-tested without configured credentials.

Public `ctx.get_config` reads `settings.policy` first, falling back to `config.policy`. Public `ctx.set_config` writes the settings subtree through the host's locked merge and atomic replacement, refuses managed settings, and preserves sibling keys. Guardian stores an effective-policy backup before calling it, checks readback, and attempts verified rollback on failure. It does not use private configuration writers. Real host tests exercise precedence, fallback, persistence and subsequent enforcement.

The policy language still has exactly `default_action`, exact-tool `rules` and `protected_paths`; no command-pattern or positive path scope was invented. Policy Lab imports the exact existing evaluator and supplies the intended home/source/storage mandatory protections. The command registration is the only entrypoint addition; the hook adapter, evaluator and decision audit implementation remain byte-for-byte unchanged from `guardian-stable`.

Policy Lab increases overlap with Policy Backtester. Distinguish reproducible hypothetical cases and minimal payload retention, not novelty in policy simulation. Automatic gap-case generation and automatic repair remain deferred.
