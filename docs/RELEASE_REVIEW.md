# Release readiness — Guardian 0.2.0, November 11, 2026

**Prepared locally; not published or submitted.** The original validated 0.1.0 tree is preserved on `guardian-stable` at `afa7733d17f2beed0d1ab6e5bd7faca4a8f1a2c2`. Upgrade work is on `guardian-upgrade`. MIT licensing, installation instructions and no third-party runtime dependencies remain. The evaluator, enforcement adapter and audit code are unchanged; the entrypoint adds only the operator CLI registration.

## Completed

- Policy Lab uses the exact live evaluator for hypothetical regression cases, with expected/actual decisions, matched rule and explanation; simulation does not execute tools or write audits.
- Conservative offline language template and optional public Hermes structured model proposal interface; strict schema/tool/path checks, clarification, no automatic activation.
- Review and exact-digest confirmation; public atomic settings update, private policy backup, readback and rollback handling.
- **87 tests on Python 3.13.7 and 3.14.9**, **194 original real-runtime checks**, **31 product integration checks**, Doctor and full validation passed. The actual product demo rehearsed in **80.00 seconds** with scripted input.
- Scanner retains the same five reviewed locations (protected AWS/SSH path literals and a disposable destructive-command example). No suppression or private runtime API workaround.
- Current catalog schema checked with the official parser; placeholders intentionally remain. See [API findings](API_FINDINGS.md) and [full actual validation](VALIDATION.md).

## Hygiene review

The reviewed source tree contains no detected genuine credentials, personal account paths, fixture audit records, temporary logs or generated binary artifacts. Credential-like strings in tests are fake redaction inputs, not real credentials. This is manual/pattern-based review, not a guarantee by a dedicated secret scanner. `.gitignore` excludes environments, caches, credential files, logs, JSONL audits, databases and build outputs. Public aggregate test results are intentional; raw integration evidence stays outside the repository. Policy proposals/backups can contain private paths and should not be uploaded.

The new CLI modules import no private Hermes internals. Only developer harnesses use actual internal dispatcher/context access to test integration. Optional model requests use `ctx.llm`; activation uses `ctx.set_config`; storage uses the documented plugin helper. Model/provider errors are redacted. All source text/Markdown links and the final diff are checked before committing.

## Remaining gates

- Explicit approval for any external write: public repository/release, catalog PR or form submission. None has occurred.
- Owner-approved GitHub namespace, maintainer and public Git identity. Local snapshots use a neutral local identity. Exact release SHA is assigned only after the final tree is committed; catalog metadata remains a draft until owner-approved publication.
- Human-recorded final demo and viewing URL; official submission form/contact fields. The owner supplied **November 11, 2026 at 5 PM EST** (22:00 UTC, 23:00 Lagos); official form rules/timezone were not independently verified here.
- Live provider inference remains unverified. The optional model interface is protocol-tested; the complete demo uses the offline template honestly. General natural-language understanding is not claimed for that template.
- Linux/CI, full model conversation, alternate UI/backends remain unverified. P1 automatic gap discovery is deferred.
- No project-only edit permission or Git push approval. No sandbox guarantee. Host auto-approval, path races/aliases, later rewrites, unsupported tools and failed loading remain limitations. Simulation is not execution proof. Activation rollback cannot be guaranteed through a persistent disk outage or concurrent external config edits; explicit recovery instructions are provided.

## Reviewable artifacts

- [Operator guide](POLICY_LAB.md)
- [Publication commands and checklist](../submission/RELEASE.md)
- [Release notes](../submission/RELEASE_NOTES.md)
- [Catalog PR body](../submission/CATALOG_PR.md)
- [Catalog draft](../submission/hermes-guardian.yaml.in)

Revalidate a clean clone of the exact approved release commit and check CI before catalog submission. Never claim catalog admission or hackathon submission merely because validation passed.
