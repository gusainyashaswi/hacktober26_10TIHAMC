# Source investigation integration

The default API now loads a public GitHub revision, resolves its immutable commit,
extracts claims, retrieves verified snippets and assesses each claim. Stage
complete means source review finished, not that a runtime bug or fix was proven.
No matching evidence leads to inconclusive findings. Failed loading or inference
produces error, not a fabricated verdict.

The public loader requests commit metadata from api.github.com and downloads an
archive from codeload.github.com at that exact SHA. It follows no redirects,
installs nothing, skips symlinks/binaries/unsupported files and bounds archive,
member and total source sizes. It trusts GitHub TLS/archive service; it does not
claim independent signed provenance verification. Rate limits are visible errors.

For offline demonstrations, an operator can set NOBLUFF_LOCAL_REPOSITORIES to a
JSON mapping of canonical GitHub identities to trusted local Git directories.
Browser requests still never select arbitrary filesystem paths. Local snapshots
read committed objects; checkout edits do not affect the analyzed revision.

Per-claim assessment keeps the model context bounded and prevents one missing
claim from blocking all others. Retrieval remains heuristic and can omit relevant
context. Source line validation proves excerpt identity, not interpretation truth.
The current comparison revision is only a requested label until verification
comparison loads it. Missing dependencies and execution remain separate work.

An explicitly injected AnalysisService without a snapshot_loader retains the
extraction-only mode for tests or embedders. Default create_app enables the real
source investigation. Run one local server worker; source workspaces are cleaned
when the application lifespan ends.

When two model assessment responses fail schema/citation validation, the claim remains explicitly inconclusive with a warning. Retrieved source remains inspectable and a reviewed reproduction test can still be approved. Transport failures remain visible errors. The system never repairs a missing citation by inventing one or accepts an invalid verdict.

A conservative English-language gate withholds conclusive source verdicts for cause/fix claims and claims containing execution-sensitive terms such as raises, crash, fail, intermittent, or an exception class. The model can misinterpret a valid excerpt; a valid citation does not make its reasoning correct. This gate is a heuristic, not a complete semantic detector. Such claims remain inconclusive until controlled evidence is available. Human review remains necessary for other model interpretations.
