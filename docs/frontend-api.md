# Maintainer workspace API — frontend handoff

Base URL defaults to `http://127.0.0.1:8000`. Keep the server on loopback. Public GitHub repositories only. No browser token field. Set optional `NOBLUFF_GITHUB_TOKEN` on the server to increase metadata API access; it is never stored in SQLite or sent to the browser. Archive source access remains public-only.

## Connect once

- `GET /api/repositories` → `{items:[{id,full_name,url,default_branch,connected_at}]}`.
- `POST /api/repositories` with `{repository:"owner/repo"}` or a GitHub URL → connected repository, HTTP 201. Reconnecting is idempotent. Maximum 20 connected repositories; a 21st new repository returns 409.
- `DELETE /api/repositories/{id}` → 204. Disconnect removes the saved connection; investigation records remain available in history.

SQLite defaults to `.nobluff/workspace.sqlite3`; override with `NOBLUFF_DB_PATH`. Saved connections and reports survive restarts. GitHub tokens are not saved. Repositories refresh on explicit requests; no webhook/background sync is claimed.

## PR inbox and details

- `GET /api/repositories/{id}/pulls?page=1` → `{items,page,has_more,refreshed_at}`. 30 open PRs per page, newest update first. Search/filter currently loaded results on the client; load additional pages as needed.
- Each item: `number,title,author,url,state,draft,updated_at,head_sha,base_sha,head_branch,base_branch`.
- `GET /api/repositories/{id}/pulls/{number}` → item plus `body,additions,deletions,changed_files,merged,head_repository,history`.
- History entries include `outdated`, comparing recorded PR head to the latest fetched PR head. Do not relabel old reports as new analyses.

## Analyse a selected PR — no copy/paste

`POST /api/repositories/{id}/pulls/{number}/analyses` with no body → HTTP 202 `{id,context}` and Location header. The backend fetches the title/body and resolves the merge base. Descriptions above 12000 characters return an explicit 422; no silent truncation.

Revision semantics:
- `report.revision`: pinned original PR merge base, used for original execution.
- `report.comparison_revision`: pinned PR head, used for fix execution.
- `report.source_revision`: pinned head reviewed by the source assessor.
- `report.source_repository`: head repository, including public forks.
- Context includes original/head/base-tip SHA, comparison basis, bounded changed-file patches and a completeness warning. This patch summary is display context, not automatically accepted evidence.

Always label “Source reviewed at” separately from “Original test revision”. For source permalinks use the source repository for head evidence; original execution remains tied to the base repository and merge base.

Poll `GET /api/analyses/{id}`. Existing verification/comparison/export routes remain unchanged. An analysis is not evidence that a test ran: inspect executions. Display backend `inconclusive` as **Unverified**.

## History

- `GET /api/repositories/{id}/investigations` → `{items:[...]}` for that repository.
- `GET /api/investigations` → recent stored investigations.
- Records include `id,created_at,repository,revision,comparison_revision,stage,context`.
- Open the report through `GET /api/analyses/{id}`, including after restart; JSON/Markdown exports work for restored reports.
- Active jobs interrupted by restart become an explicit error on restoration. They do not silently resume or claim completion. Restart completed investigations can reload pinned source for subsequent approved verification.

## Error handling

404: missing connection, missing PR, unavailable/private repository.
422: invalid input, unsupported private repository, or oversized PR description.
429: local capacity, repository connection limit, or GitHub restricted/rate-limited access.
502: GitHub/network/metadata problem.
503: persistent workspace disabled in an injected test/development service.

All errors use `{detail:"..."}`. Preserve selected repository/PR and entered test drafts on errors. Never silently substitute fixtures. API health's configured model is not a live readiness guarantee.
