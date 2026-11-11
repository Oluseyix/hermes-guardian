Hermes Guardian 0.1.0 provides deterministic allow/approve/block policies through the native pre_tool_call hook, explicit local protected paths, conservative shell handling and payload-free persistent decision audits. It has no third-party runtime dependencies.

Verified on official Hermes 0.23.1, macOS arm64: 63 unit tests and 194 real-runtime checks passed. Doctor and full validation passed with reviewed scanner cautions. See docs/VALIDATION.md and docs/RELEASE_REVIEW.md for exact evidence and limits.

This is a policy hook, not a sandbox. Host automatic-approval settings can bypass approval requests; protected block decisions remain blocks. Local path races, aliases, later argument rewriting, unrecognized adapters, disabled plugins and untested backends limit coverage. Audit records represent decisions, not execution or final consent. Linux CI remains pending at preparation time.
