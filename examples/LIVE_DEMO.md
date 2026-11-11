# Optional real-Hermes smoke test

This optional model-driven/manual procedure was **not executed** during this build. Real Hermes tool dispatch and the host's terminal approval prompt were separately tested by `tests/run_hermes_matrix.py` with scripted PTY responses; see the validation report. For this manual procedure use a separate local profile, a local terminal/file backend, and no argument-rewriting plugins. Run the official validator and doctor first. Do not use real credentials as fixtures.

1. In your own terminal, create a temporary directory containing `public.txt` with harmless text, and `vault/key.txt` with the text `DEMO_ONLY`. Record the directory's absolute path. Keep it outside the Guardian source directory and Hermes home, which are automatically protected.
2. Install and enable Guardian in that profile as described in the README. Configure `protected_paths` with the **absolute path to the fixture's `vault` directory**, `action: block`; keep the four default tool rules and `default_action: block`. Merge settings without deleting existing profile configuration. Restart Hermes.
3. Confirm that approvals are enabled and YOLO is off. For each request below, inspect the actual tool name and arguments emitted by the model. If it emits a different call, that is not the same test. Substitute the real absolute fixture path for `/FIXTURE`.

| Requested call | Expected Guardian decision / host observation |
|---|---|
| `read_file`, `{"path":"/FIXTURE/public.txt"}` | Allow; normal file result unless another host guard refuses it. |
| `write_file`, `{"path":"/FIXTURE/public.txt","content":"APPROVED_DEMO"}` | Approve directive; choose **Deny**, verify file unchanged outside Hermes. Repeat and choose **Once**, verify file changed. |
| `read_file`, `{"path":"/FIXTURE/vault/key.txt"}` | Hard block; fixture contents must not be returned by this call. |
| `terminal`, `{"command":"rm -rf /FIXTURE/vault"}` | Hard block; verify the fixture still exists outside Hermes. Only use this disposable fixture. |
| `terminal`, `{"command":"pwd && pwd"}` | Hard block for unsupported compound syntax, despite the benign example. |
| `execute_code`, `{"code":"print('demo')"}` | Default block. |

4. Inspect `<profile home>/plugin-data/hermes-guardian/audit.jsonl` **from your own terminal**, not an agent tool. There should be decision records without raw paths, contents, commands, or task IDs. An `approve` record is not a record of the person's answer.
5. Exercise unattended approval in the host's documented deny mode; confirm no prompt hangs and the write does not run. Test timeout behavior with the host's supported approval timeout settings. Do not infer these results from the policy-only demo.
6. Disable Guardian as the operator and remove only the disposable fixture when done. Keep/archive audit records as desired.

The model may refuse to emit a requested test or choose a different tool. The standalone suite provides deterministic exact-call coverage; this procedure checks the actual host integration and user approval experience.
