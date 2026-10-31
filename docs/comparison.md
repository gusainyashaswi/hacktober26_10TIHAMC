# Same-test before/after check

Submit an analysis with an original `revision` and `comparison_revision`. After source investigation completes, POST the reviewed verification plan to `/api/analyses/{id}/comparison` with `approved: true`. The comparison revision is pinned before any execution. The exact same test bytes run against both snapshots in a local immutable Docker image. Both logs, revisions, command, test SHA256, statuses, and image IDs remain in the report and its exports.

- `fix_verified_for_test`: original fails with the declared exception in a pytest error line; the proposed fix passes. Test hashes and immutable image IDs match, and revisions differ.
- `not_reproduced_for_test`: the approved test passed on the original snapshot. This does not disprove the issue.
- `still_failing`: the original reproduced the declared exception and the test still fails after the change. The second failure may have another cause; inspect both logs.
- `inconclusive`: setup failure, timeout, unknown error, same revision, or incomparable image. No fix claim is made.

This verifies a regression test, not the completeness of an entire fix or PR. One comparison is recorded per analysis; create a fresh analysis to try another revision. The model interprets source claims; it does not control the command, status classifier, or comparison verdict.
