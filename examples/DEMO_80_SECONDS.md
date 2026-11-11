# 80-second live demonstration

Use official Hermes **0.23.1** and its installed Python, with the matching source tree. This developer harness uses actual plugin discovery, tool dispatch and the native terminal approval prompt. It does not use a model, mock outputs or patch Hermes. It creates a new isolated Hermes home and harmless fixtures under `/tmp`; it never replaces an existing profile. Run in a terminal, with provider credentials removed from the environment (they are not needed).

```sh
# Set these to your existing isolated installation, not your system Python.
HP=/absolute/path/to/hermes/venv/bin/python
HS=/absolute/path/to/hermes-source
PYTHONDONTWRITEBYTECODE=1 "$HP" tests/live_demo.py --source "$HS"
```

Start recording when `LIVE:` appears, after imports. The four cues are timed from that line; the runner finishes at 80 seconds. Choose **o / Once** promptly at the real prompt, before the 45-second cue. Denial, timeout or a failed assertion means the demonstration failed: rerun honestly. Never splice in substitute results. The final temporary path identifies the disposable fixtures; inspect or remove only that directory after recording. Keep recordings and raw logs outside the repository.

| Time | Screen and suggested narration |
|---|---|
| 0–10 | “Hermes Guardian is a standalone policy plugin running inside real Hermes 0.23.1. This demo uses harmless temporary files and the actual tool dispatcher, without a model.” |
| 10–25 | “A normal read is allowed. You can see the file tool return our public fixture. Guardian evaluates explicit tool rules and protected paths before execution.” |
| 25–45 | “Writing requires approval. This is Hermes’s own approval prompt. I choose Once, and the file is written. Guardian does not implement a separate approval interface.” **Press o, Enter.** |
| 45–60 | “Now the same write tool targets our protected directory. Guardian blocks it without offering approval. An independent check confirms the original harmless content remains unchanged.” |
| 60–80 | “These are the persisted audit records, read by the operator. They contain decisions and redacted arguments, not file contents or paths. Approval means a request, not proof of the answer. Guardian is not a sandbox: it depends on loading, host settings, trusted plugins and local path semantics.” |

Rehearsal results are in [RELEASE_REVIEW.md](../docs/RELEASE_REVIEW.md). The recorded rehearsal uses scripted `o` on a real PTY; a human-recorded video is still required. The earlier optional model-driven procedure remains in [LIVE_DEMO.md](LIVE_DEMO.md).
