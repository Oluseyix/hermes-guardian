# Publication procedure — approval required

Nothing in this document has been pushed or submitted. Run the local review first. Obtain explicit owner approval before the external-write section. Missing values must come from the owner; do not infer public identity from local account names.

## Local preparation

From the project root, review the license, README, limitations, release report and every staged file. Set Git identity to the approved public name/email (a GitHub noreply address is fine). The original validated tree is preserved on local `guardian-stable`; work continues on `guardian-upgrade`. Do not delete or rewrite that baseline. The snapshot author is a neutral local identity; choose an approved public identity for any subsequent release edits:

```sh
git switch guardian-upgrade
git show --stat guardian-stable
git config user.name 'APPROVED PUBLIC NAME'
git config user.email 'APPROVED PUBLIC EMAIL'
git add .github .gitignore LICENSE README.md __init__.py plugin.yaml guardian tests examples docs submission demo.py verify.py guardian_lab.py
git diff --cached --check
git diff --cached --stat
git diff --cached
# Ensure no credentials, local logs, audit files, caches or private paths are staged.
python3 verify.py --require-hermes
hermes plugins doctor "$PWD" --ci
hermes plugins validate "$PWD" --install-deps
# Commit only if reviewed changes remain after the prepared local upgrade commit.
git commit -m 'Release Hermes Guardian 0.2.0'
git status --short
git rev-parse HEAD
```

Hermes must be the isolated 0.23.1 installation on the child process PATH; see the validation report for the wrapper used during testing. Do not install or change a global Hermes profile just to run these commands. Review Git identity before committing. CI matrix results are not yet available.

## External writes — only after explicit approval

Install/authenticate GitHub CLI if necessary using the owner's account, then confirm the intended account and namespace. Do not paste tokens into commands or files.

```sh
OWNER='APPROVED_GITHUB_OWNER'
REPO="$OWNER/hermes-guardian"
gh auth status
gh repo create "$REPO" --public --source=. --remote=origin
# Review remote URL before publishing.
git remote -v
git push -u origin HEAD:main
SHA=$(git rev-parse HEAD)
git tag -a v0.2.0 "$SHA" -m 'Hermes Guardian 0.2.0'
git push origin v0.2.0
gh release create v0.2.0 --repo "$REPO" --verify-tag --title 'Hermes Guardian 0.2.0' --notes-file submission/RELEASE_NOTES.md
```

Confirm the public repo is readable, CI passes and the pinned commit contains exactly the reviewed files. Verify from a fresh clone at `$SHA`, running Doctor and full validation again. README currently describes unpublished status accurately: update that paragraph and installation URL before the final release commit if publication is approved, then revalidate the final tree. A subsequent change requires a new reviewed SHA; never silently repoint a release tag.

## Catalog PR — separate explicit approval

Follow the [official requirements](https://hermes-agent.nousresearch.com/docs/developer-guide/plugins/catalog-submission). The owner or major contributor submits one new catalog YAML, not plugin runtime code, to the official repository. Use the public URL, full 40-character released SHA and approved maintainer in the draft. Do not submit `.yaml.in` or placeholders. Version, floor and capabilities must match `plugin.yaml`.

From a separate working directory after approval:

```sh
gh repo fork NousResearch/hermes-agent --clone
cd hermes-agent
git switch -c catalog/hermes-guardian
# Copy the reviewed draft, then replace its three placeholders with real values.
cp /absolute/path/to/hermes-guardian/submission/hermes-guardian.yaml.in plugin-catalog/hermes-guardian.yaml
# Edit repo, sha, maintainer. Review all metadata and disclosures.
git diff --check
git diff -- plugin-catalog/hermes-guardian.yaml
rg '<PUBLIC_|<FULL_|<OWNER_' plugin-catalog/hermes-guardian.yaml
# The preceding rg must have no matches (exit 1).
git add plugin-catalog/hermes-guardian.yaml
git commit -m 'catalog: add Hermes Guardian 0.2.0'
git push -u origin catalog/hermes-guardian
gh pr create --repo NousResearch/hermes-agent --base main --head "$OWNER:catalog/hermes-guardian" --title 'catalog: add Hermes Guardian' --body-file /absolute/path/to/hermes-guardian/submission/CATALOG_PR.md
```

Review that the PR changes only one YAML. Use the correct fork owner in `--head` if different from `$OWNER`. Catalog admission is reviewer-controlled, not guaranteed by validator success. Every future pin change needs another PR.

## Final hackathon checklist

- [ ] Confirm official deadline/timezone and form URL; user-supplied deadline is November 11, 2026 at 5 PM EST (22:00 UTC / 23:00 Lagos), supplied by the owner. The official form URL has not been verified here.
- [ ] Owner approves public repo namespace, maintainer, public Git identity and MIT licensing.
- [ ] Public release URL, exact SHA and version agree; clean-clone validation and CI pass.
- [ ] Preserve scanner cautions and limitations; do not claim sandboxing or complete tool coverage.
- [ ] Review official form's required team/contact/license/demo fields; supply owner-approved values.
- [ ] Obtain separate approval for catalog PR and hackathon form submission.
- [ ] Record final URLs and submission receipt after actual submission; never claim admission beforehand.
