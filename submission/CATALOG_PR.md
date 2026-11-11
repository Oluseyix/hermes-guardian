Adds Hermes Guardian, a standalone native plugin with one pre_tool_call hook and no tools, middleware or third-party runtime dependencies. The submitted YAML must pin the owner-approved public release commit before opening this PR.

Guardian evaluates deterministic rules, protected local POSIX paths and a deliberately small shell grammar. It delegates approval to Hermes and keeps metadata-only decision audits. Existing security plugins overlap substantially; the distinction is its narrow local scope, payload minimization and lack of an SDK, external service or model reviewer, not a new security category.

Runtime disclosure: reads settings and filesystem metadata/symlink targets, writes owner-only redacted JSONL in sanctioned plugin storage, and does not read credential-file contents, make network/model calls, spawn subprocesses or modify core. Development harnesses invoke the real host and are not plugin dependencies.

Hermes 0.23.1 Doctor and full validate --install-deps passed on macOS arm64. 63 unit tests and 194 runtime checks passed. The validator reports reviewed AWS/SSH protected-path literal cautions and a destructive-command literal in a disposable manual demo; these are not suppressed. See repository validation and release-review reports for final-tree results.

Not a sandbox. Approval follows host settings; path aliases/races, later plugin rewrites, unsupported tool adapters and failed loading limit coverage. Audit records are decisions, not proof of execution or consent. Linux and full model/UI flows remain unverified at preparation time.

Before submission: replace this paragraph with the actual public URL, released SHA, clean-clone validation results, CI results, and confirmation that the submitter is the owner or a major contributor. Do not submit this preparation placeholder.
