# Retrieval review and shared contract integration

Reviewed Yogye Berry's provisional module at
https://github.com/YogyeBerry/nobluff-retrieval/tree/bf87384e2cf0afe646e0a06b7988e5fcd91dcd6f.
This integration retains his Snapshot/SnapshotFile/Excerpt design and pinned Git
object reading approach, with attribution in retrieval.py. It adds the shared
Claim-to-Evidence adapter rather than changing the public product contracts.

Changes found necessary: check blob size before reading it, cap subprocess output,
apply Git deadlines, skip invalid UTF-8 instead of claiming replacement text is
exact source, disable replacement objects and unwanted global Git config, and
validate excerpt coordinates and contents before constructing Evidence.

Line coordinates are one-based and inclusive; excerpts normalize line separators
with newline joins. They are not claimed to preserve original byte line endings.
Snapshot.commit is immutable; Evidence.revision uses that exact commit. Stable
IDs derive from revision, path, range and text. Files outside the supported set,
symlinks and binary content are skipped. Retrieval is heuristic and incomplete;
no match is not evidence that a claim is false.

load_local_snapshot is for explicit local operator input, not arbitrary paths
from the browser. No project code, tests or installation hooks run during loading.
The public GitHub loader is a separate pipeline integration step.
