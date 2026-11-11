# Release readiness review — November 11, 2026

**Prepared, not published.** No GitHub repository, push, release, PR or form submission was created. The project still has no Git history. MIT license, native manifest, installation/configuration instructions and explicit limitations are present. No runtime or manifest changes were made during this release review; SHA-256 comparisons against the review baseline confirm that.

## Hygiene and security review

Reviewed runtime imports, policy/approval/audit boundaries, the manifest, dependency declarations, public documentation and the full file inventory. No release-blocking runtime defect was found. No genuine credentials, private account paths, binary/generated artifacts, symlinks, temporary logs or audit records were found in the release tree. Pattern matches for a private-key header and credential-like strings are deliberately fake redaction-test inputs; they contain no key body or real credential. This was a manual and pattern-based review, not a claim that an automated secret scanner proved absence of secrets; gitleaks was not installed.

Sanitized personal absolute paths and generated environment IDs in the historical validation report while retaining versions, outcomes and reproducible command structure. Expanded `.gitignore` for environments, caches, secret files, logs, JSONL audits, databases and generated outputs. Ignore rules do not replace staged-content review. Raw host transcripts, fixture audit records and environment details remain outside this tree. `docs/verification-results.json` is intentional public aggregate test evidence, not an audit log. Zero third-party plugin runtime dependencies remain; development tests use the installed host.

The new live demo is a developer harness in `tests/`, never imported by the plugin. Its actual host-dispatch imports are intentionally internal integration-test surfaces, not runtime API dependencies. Initial placement in `examples/` generated a validator private-import warning; moving the unchanged harness to the established test boundary removed that warning. This is not a claim that those test APIs are stable.

## Verification and commands

Run from the project root, with `IG` = isolated integration storage, `HS` = official v0.23.1 source and `HP` = its installed Python. The local launcher strips inherited provider credentials and sets private runtime/cache roots. Local path values are deliberately omitted from public documentation.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -q
python3 "$IG/run.py" "$HS/.hermes/bin/hermes" plugins doctor "$PWD" --ci
python3 "$IG/run.py" "$HS/.hermes/bin/hermes" plugins validate "$PWD" --install-deps
python3 "$IG/run.py" "$HP" tests/live_demo.py --source "$HS"
```

- **63 unit tests passed** in the final review; no runtime changes.
- **Doctor exit 0**: one hook, zero tools.
- **Full validation with dependency installation exit 0**, with the same five reviewed scanner locations: AWS/SSH protected-path literals and the disposable destructive-command example. These warnings are retained, not suppressed. Host isolation is not a sandbox.
- **80.00-second actual-runtime rehearsal passed**, real read result, native approval prompt answered Once, successful harmless write, protected write refused with unchanged fixture, and three genuine persisted audit decisions. The PTY answer was scripted for rehearsal. A human-recorded final video is still outstanding.
- Earlier validated **194 integration checks / seven contexts** and **100 audit concurrency runs** remain documented in [VALIDATION.md](VALIDATION.md); those larger suites were not rerun during this documentation-only/runtime-unchanged release review.

Private evidence filenames: `logs/release-doctor.log`, `logs/release-validate.log`, `logs/release-demo-rehearsal.log`; baseline `release-runtime-baseline.json`. These files are outside the release repository and should not be uploaded wholesale.

## Current catalog review

Reviewed the [official submission requirements](https://hermes-agent.nousresearch.com/docs/developer-guide/plugins/catalog-submission), [catalog README](https://github.com/NousResearch/hermes-agent/blob/main/plugin-catalog/README.md), and downloaded current official `hermes_cli/plugin_catalog.py`. Parser snapshot SHA-256: `8bd878172be6b5ad6f4bc45fffa4bee54c815f38b59e8f3bf13c836de66d26ef`.

Executed that parser against the draft: **rejected as expected** because publication metadata is missing. An in-memory synthetic HTTPS URL, 40-hex SHA and maintainer produced an accepted shape; name, version, minimum Hermes version, platforms and declared hook/tool/environment capabilities matched the native manifest. Synthetic values were never written into the draft. This proves schema compatibility, not repository existence, commit validity, catalog acceptance or completion of publication checks.

Public HTTPS URL, full released commit pin and owner-approved maintainer remain mandatory. New pin updates require reviewed catalog PRs. Runtime behavior must be disclosed; prepared PR text includes filesystem metadata access, local audit writes, scanner cautions and limitations. See [API_FINDINGS.md](API_FINDINGS.md#catalog-comparison) for the reviewed 1,578-entry catalog snapshot. Guardian overlaps existing permission/security plugins; its limited distinction is a small local deterministic implementation with no external SDK/service/model dependency and payload-free decision audits.

## Remaining release gates and risks

- Owner-approved GitHub namespace/repository URL, maintainer and public Git name/email; released commit SHA cannot exist until the reviewed tree is committed.
- Human-recorded 75–85 second video, official form URL, deadline timezone and required participant/contact fields remain unverified or missing.
- Linux/CI, full model-driven conversations and gateway/Desktop/TUI UI remain unverified. The tested platform is macOS arm64 with Hermes 0.23.1 / Python 3.14.9.
- Guardian is not a sandbox. Host automatic-approval settings, path aliases/races, later argument changes, explicitly allowed unknown tools and disabled/failed loading limit enforcement. Audit failures block availability; audit entries are decisions, not consent or execution proof.
- Revalidate the exact clean public release commit and review CI before submitting a catalog entry. Do not call the project catalog-listed or hackathon-submitted before those events occur.

Prepared artifacts: [demo cue sheet](../examples/DEMO_80_SECONDS.md), [publication commands/checklist](../submission/RELEASE.md), [release notes](../submission/RELEASE_NOTES.md), [catalog PR body](../submission/CATALOG_PR.md), and [unfilled catalog draft](../submission/hermes-guardian.yaml.in). External writes require explicit owner approval.
