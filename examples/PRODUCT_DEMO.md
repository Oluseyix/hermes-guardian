# Product demo — 80 seconds on real Hermes 0.23.1

Use the installed Hermes 0.23.1 Python and matching official source. Run from the project root, with provider credentials absent; the demo uses the offline language template. It creates only harmless fixtures and a new Hermes home under `/tmp`, loads the actual plugin, checks actual CLI registration, and uses the real public settings API and native tool dispatcher. No model output or host response is fabricated.

```sh
HP=/absolute/path/to/hermes/venv/bin/python
HS=/absolute/path/to/hermes-source
PYTHONDONTWRITEBYTECODE=1 "$HP" tests/product_integration.py --source "$HS" --demo
```

Start recording at `LIVE:`, after startup checks. Prompts require real input; delayed answers can extend the demo, so rehearse first. A failure, denial or timeout is a failed take, not an invitation to splice in fake results. Final elapsed time must be 75–85 seconds.

| Time | Action / narration |
|---|---|
| 0–10 | Type: `Hermes can edit my coding projects, but must ask before deleting files or pushing code to GitHub.` Say: “Guardian turns permissions into reviewable rules. This is the offline builder running with real Hermes.” |
| 10–20 | Show the clarification. “It refuses to invent project-scoped permissions or Git push approval. Those exceed the current evaluator.” |
| 20–30 | Type: `Ask before edits and deletions; block GitHub pushes.` “I explicitly choose the conservative alternative. The proposed rules preserve protected paths.” |
| 30–40 | Show seven Lab results. “These hypothetical calls use the same evaluator as enforcement. Nothing executes. Git push is blocked; deletion asks; protected paths take precedence.” |
| 40–55 | Review limitations, then type the displayed **full** `ACTIVATE <digest>` at `Confirmation:`. “I approve this exact proposal. Hermes saves it atomically, with a backup and verified readback.” |
| 55–60 | Show actual allowed file read. “Now the real file tool returns our harmless fixture.” |
| 60–72 | At the native prompt type **o**, Enter. “This is Hermes’s own approval gate. Once allows the harmless write.” |
| 72–80 | Show protected write refusal and genuine audit records. “The protected file stays unchanged. Audits record decisions, not final consent. Guardian is a policy hook, not a sandbox.” |

For a clearly labelled scripted-input rehearsal (not a human recording):

```sh
PYTHONDONTWRITEBYTECODE=1 "$HP" tests/rehearse_product_demo.py \
  --source "$HS" --log /absolute/private/path/product-demo.log
```

This PTY runner sends the two instructions, the exact confirmation digest, and `o` to real prompts. The log contains actual outputs and temporary fixture paths. Keep logs and fixture audit files outside the public repository. The original 0.1.0 demo is retained for reference, but this is the 0.2.0 submission demo. A human-recorded final video and its public URL remain outstanding.
