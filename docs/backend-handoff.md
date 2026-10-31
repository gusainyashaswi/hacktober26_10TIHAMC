# NoBluff Backend Handoff: Repository Persistence & Pull Request Ingestion

This document establishes the typed contract and integration specification between the NoBluff frontend (owned by Devishi) and the backend orchestration lead (Gurmehar) for the **Connect Once** maintainer workflow.

The current backend API (`backend/src/nobluff/api.py`) provides analysis orchestration, claim extraction, snapshot retrieval, report export (`/api/analyses/{id}/export`), and controlled verification (`/api/analyses/{id}/verification` & `/comparison`). However, durable repository persistence across sessions and automated GitHub pull request ingestion are not yet connected server-side.

Until these endpoints land, the frontend maintains a client-side session store alongside an isolated, explicitly labeled **Development Adapter** (`frontend/src/api/devAdapter.ts`).

---

## 1. Required Operations

| Method | Endpoint | Description | Status |
|---|---|---|---|
| `GET` | `/api/repositories` | List connected repositories | **Proposed** |
| `POST` | `/api/repositories` | Connect and validate a GitHub repository | **Proposed** |
| `DELETE` | `/api/repositories/{id}` | Disconnect a repository | **Proposed** |
| `GET` | `/api/repositories/{id}/pulls` | List open pull requests for connected repo | **Proposed** |
| `GET` | `/api/repositories/{id}/pulls/{number}` | Fetch PR metadata, description, & pinned revisions | **Proposed** |
| `POST` | `/api/analyses` | Submit analysis (optionally linking `pr_number`) | **Implemented** |
| `GET` | `/api/analyses/{id}` | Poll analysis progress and report | **Implemented** |
| `GET` | `/api/analyses/{id}/export` | Download report as JSON or Markdown | **Implemented** |
| `POST` | `/api/analyses/{id}/verification` | Run approved test in Docker | **Implemented** |
| `POST` | `/api/analyses/{id}/comparison` | Run identical test on base and fix revisions | **Implemented** |

---

## 2. Request & Response Shapes

### 2.1 Connect Repository (`POST /api/repositories`)

Accepts a public GitHub repository identity in `owner/repo` or canonical HTTPS format.

```json
// Request
{
  "repository": "pallets/flask"
}

// Response (201 Created)
{
  "id": "pallets/flask",
  "owner": "pallets",
  "name": "flask",
  "full_name": "pallets/flask",
  "url": "https://github.com/pallets/flask",
  "default_branch": "main",
  "is_private": false,
  "connected_at": "2026-11-01T04:30:00Z"
}
```

#### Error States:
- `400 Bad Request`: Invalid repository URL or string format.
- `401 Unauthorized / 403 Forbidden`: Private repository requiring GitHub authentication token, or rate limit hit.
- `404 Not Found`: Repository does not exist on GitHub.

---

### 2.2 List Open Pull Requests (`GET /api/repositories/{id}/pulls`)

Returns the current open pull requests for the repository.

#### Query Parameters:
- `state`: `open` (default), `closed`, `all`
- `page`: integer (default: 1)
- `per_page`: integer (default: 30, max: 100)

```json
// Response (200 OK)
{
  "total_count": 12,
  "page": 1,
  "per_page": 30,
  "items": [
    {
      "id": "flask-4892",
      "number": 4892,
      "title": "Fix request argument parsing when query string contains malformed percent-encoded sequences",
      "author": "untitaker",
      "source_branch": "fix-malformed-query-encoding",
      "target_branch": "main",
      "base_commit": "d5c21f0a82e75e5eb461b203498a964e52b2ef81",
      "head_commit": "f849a64e1c28c89b2751f7253507d62058fa72da",
      "updated_at": "2026-10-28T14:30:00Z",
      "created_at": "2026-10-26T09:12:00Z",
      "is_draft": false,
      "html_url": "https://github.com/pallets/flask/pull/4892",
      "latest_analysis_id": "analysis-1234",
      "latest_analysis_stage": "complete",
      "analysed_head_commit": "f849a64e1c28c89b2751f7253507d62058fa72da"
    }
  ]
}
```

---

### 2.3 Pull Request Metadata & Pinned Revisions (`GET /api/repositories/{id}/pulls/{number}`)

Returns full PR description, changed files, and immutable commit hashes selected by the backend comparison resolver.

```json
// Response (200 OK)
{
  "id": "flask-4892",
  "number": 4892,
  "title": "Fix request argument parsing when query string contains malformed percent-encoded sequences",
  "author": "untitaker",
  "source_branch": "fix-malformed-query-encoding",
  "target_branch": "main",
  "base_commit": "d5c21f0a82e75e5eb461b203498a964e52b2ef81",
  "head_commit": "f849a64e1c28c89b2751f7253507d62058fa72da",
  "description": "When parsing malformed query strings with invalid percent-encodings...",
  "is_draft": false,
  "html_url": "https://github.com/pallets/flask/pull/4892",
  "changed_files": [
    {
      "path": "src/flask/wrappers.py",
      "status": "modified",
      "additions": 14,
      "deletions": 3
    },
    {
      "path": "tests/test_basic.py",
      "status": "modified",
      "additions": 22,
      "deletions": 1
    }
  ],
  "total_additions": 36,
  "total_deletions": 4
}
```

---

## 3. Revision Semantics & Stale Analyses

1. **Comparison Basis Rule:**
   The frontend must never guess the original pre-fix revision from a branch name.
   The backend must resolve and pin the exact `base_commit` (merge base) and `head_commit`.
2. **Head Invalidation Rule:**
   When a maintainer pushes new commits to an open PR, its `head_commit` changes on GitHub.
   If an existing analysis exists where `analysed_head_commit != pr.head_commit`, the frontend marks the analysis status as `outdated`.
   The old report remains bound to its original immutable commit SHAs. It is never silently relabeled as current.
   The maintainer is offered an explicit action: **"Analyse latest revision"**.

---

## 4. Persistence Expectations

- **Server-Side Durability:**
  Connected repositories and past investigation reports should be stored in a durable SQLite database or append-only file log (e.g. `~/.nobluff/nobluff.db`).
- **Process Memory Limitation:**
  Currently, reports reside in a single process memory store (`bounded to 100 per server process`). Server restarts purge all active and past reports. The UI explicitly alerts maintainers that server history is process-local until durable persistence lands.

---

## 5. Authentication & Rate-Limiting Policy

- **No Browser Token Storage:**
  Maintainer Personal Access Tokens (PAT) must never be entered or stored in the browser `localStorage`.
- **Public Repositories First:**
  Public repositories do not require maintainer credentials. The backend loader queries `api.github.com` and `codeload.github.com`.
- **Rate-Limit Visibility:**
  When GitHub unauthenticated rate limits (60 req/hr) are reached, the API must return `429 Too Many Requests` or `SnapshotError("GitHub denied access or rate-limited this request")` with clear retry guidance.
