# NoBluff Frontend

Minimalist, evidence-based triage workspace for open-source maintainers. Built with React 18, TypeScript, and Vite.

## Architecture & Principles

NoBluff helps maintainers investigate technical claims made in issues and pull requests:
- **Connect Once Workflow:** Maintainers connect a repository once (`owner/repo` or canonical GitHub URL). NoBluff remembers the connected repository across sessions and loads its open pull requests into a selectable triage inbox.
- **Inspectable Evidence:** Every claim extracted by local Qwen3-8B is linked directly to exact source excerpts, line ranges, and pinned commit SHAs. Inconclusive findings explain missing evidence rather than pretending certainty.
- **Explicit Test Approval:** No container code runs automatically. Maintainers review focused pytest reproduction test code and must explicitly check an approval box before execution. Any edit immediately resets approval.
- **Controlled Docker Verification:** Approved tests run inside unprivileged, network-isolated Docker containers with strict CPU, memory, and time limits. Pytest collection errors are labeled Setup Errors, not bug reproductions.
- **Same-Test Comparison:** Side-by-side comparison of original and proposed fix revisions using verified identical test bytes (`SHA256`). Results are scoped strictly to the approved test and recorded environment.
- **Process Memory & Persistence:** The backend currently stores analyses in memory (up to 100 per server process). See `docs/backend-handoff.md` for the planned durable persistence contract.

---

## Visual Design

- **Palette:** Warm off-white background (`#faf9f6`), white working surfaces, dark charcoal text (`#1c1917`), and a single muted forest-green accent (`#235332`) for primary actions.
- **Verdicts:** Muted forest green (`supported`), muted red (`contradicted`), muted amber (`inconclusive`). Colors are always accompanied by explicit text labels.
- **Typography:** Inter/System sans-serif for interface elements; system monospace for code, commit hashes, and test signatures.
- **Restraint:** No neon colors, gradients, decorative charts, chatbot layouts, fake activity feeds, or emoji interface icons. Clean SVG outline icons throughout.

---

## Getting Started

### 1. Requirements

- Node.js >= 18 (audited with Node 22 LTS)
- npm >= 9

### 2. Install Dependencies

```bash
cd frontend
npm ci
```

### 3. Start Development Server

```bash
npm run dev
```

The Vite dev server starts at `http://127.0.0.1:5173`. CORS headers on the local FastAPI backend permit requests from `http://localhost:5173` and `http://127.0.0.1:5173`.

### 4. Running Backend Server (Local API)

From the repository root with Ollama running:

```bash
python -m pip install -e './backend[dev]'
python -m uvicorn nobluff.api:create_app --factory --host 127.0.0.1 --port 8000
```

### 5. Type Checking

```bash
npm run typecheck
```

### 6. Running Tests

```bash
npm run test -- --run
```

All 20 unit and integration tests exercise:
- Connecting a repository once and restoring saved selection.
- Loading pull requests and filtering/searching.
- Selecting PRs and extracting metadata without manual pasting.
- Submitting analysis with backend-provided comparison context.
- Tracking progress and stopping polling at terminal stages.
- Opening evidence drawers with exact line numbers and permalinks.
- Honest inconclusive and missing-evidence handling.
- Explicit reproduction approval and edit-based approval resets.
- Setup errors and timeouts classification.
- Same-test before/after scoped comparison.
- Outdated analysis detection when PR head commit changes.
- Isolated development adapter labeling.

### 7. Production Build

```bash
npm run build
```

Bundles production-optimized static assets to `dist/`.
