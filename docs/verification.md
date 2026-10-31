# Approved controlled verification

Yashaswi's `verification/runner.py` is integrated behind a snapshot and approval policy. Enable with `NOBLUFF_ENABLE_VERIFICATION=1`. Build the local image first: `docker build -t nobluff-runner:ci runner`.

POST `/api/analyses/{id}/verification` with `claim_id`, reviewed `test_code`, `approved: true`, and optional `expected_failure` (an exception class name). Analysis must be complete. The fixed pytest command runs only in Docker; no host execution fallback exists.

The adapter copies committed, validated snapshot text into a temporary directory. The live checkout, its Git credentials, Docker socket, and host environment are not mounted. The image is resolved to a local immutable ID before execution. Container controls: no network, non-root, read-only source/root filesystem, dropped capabilities, no privilege escalation, one CPU, 256 MB memory, 64 PIDs, and a 15-second run deadline. Both log streams are drained with bounded retained memory. Cleanup removes the named container. Docker Desktop is required on macOS.

Python 3.11 and pytest are included. Dependencies are not auto-installed; missing imports and pytest collection errors are setup errors, not reproduced bugs. The runner is a hackathon containment layer, not a proven hostile-code isolation service. Run the local API on loopback only.

A declared exception must appear as a pytest error line, not merely as text in a test's source. Even this supports only the approved test: a human must judge whether that test represents the issue. Passing a single test does not disprove a general bug report. Static findings retain their limits when execution is inconclusive.

CI now includes a separate Docker runner job, in addition to backend and frontend jobs. Real Docker tests are marked `runner`; the other jobs remain usable without Docker or model downloads.
