import {
  ConnectedRepository,
  PullRequest,
  PullRequestDetail,
} from '../types/repository';

export interface RepositoryConnectionResult {
  repository: ConnectedRepository;
  notice: string;
}

// Built-in curated open-source development fixtures
const KNOWN_REPOSITORIES: Record<string, { repo: ConnectedRepository; prs: PullRequestDetail[] }> = {
  'pallets/flask': {
    repo: {
      id: 'pallets/flask',
      owner: 'pallets',
      name: 'flask',
      fullName: 'pallets/flask',
      url: 'https://github.com/pallets/flask',
      defaultBranch: 'main',
      isPrivate: false,
      connectedAt: new Date().toISOString(),
    },
    prs: [
      {
        id: 'flask-4892',
        number: 4892,
        title: 'Fix request argument parsing when query string contains malformed percent-encoded sequences',
        author: 'untitaker',
        sourceBranch: 'fix-malformed-query-encoding',
        targetBranch: 'main',
        baseCommit: 'd5c21f0a82e75e5eb461b203498a964e52b2ef81',
        headCommit: 'f849a64e1c28c89b2751f7253507d62058fa72da',
        updatedAt: '2026-10-28T14:30:00Z',
        createdAt: '2026-10-26T09:12:00Z',
        isDraft: false,
        htmlUrl: 'https://github.com/pallets/flask/pull/4892',
        description: `### Description
When parsing malformed query strings with invalid percent-encodings like \`%ZZ\` or truncated sequences like \`%A\`, \`urllib.parse.parse_qs\` raises a \`UnicodeDecodeError\` or \`ValueError\` instead of treating it as an invalid query parameter.

Under certain WSGI gateways, this results in an unhandled 500 error instead of a graceful 400 Bad Request.

### Proposed Changes
- In \`src/flask/wrappers.py\`, wrap query string unquoting with a try/except block.
- Convert unquote parse errors to \`BadRequestKeyError\` or empty parameter fallback.
- Added pytest reproduction in \`tests/test_basic.py\`.`,
        changedFiles: [
          {
            path: 'src/flask/wrappers.py',
            status: 'modified',
            additions: 14,
            deletions: 3,
          },
          {
            path: 'tests/test_basic.py',
            status: 'modified',
            additions: 22,
            deletions: 1,
          },
        ],
        totalAdditions: 36,
        totalDeletions: 4,
      },
      {
        id: 'flask-4904',
        number: 4904,
        title: 'Prevent recursive loop when nesting blueprints with empty url_prefix',
        author: 'davidism',
        sourceBranch: 'blueprint-prefix-recursion',
        targetBranch: 'main',
        baseCommit: 'e28b8a53173d6b057c32bfdb07f5d6ee4680ea3b',
        headCommit: 'a93b58913d317072a24c0840b2a7587ea0b75a41',
        updatedAt: '2026-10-30T18:45:00Z',
        createdAt: '2026-10-29T11:00:00Z',
        isDraft: false,
        htmlUrl: 'https://github.com/pallets/flask/pull/4904',
        description: `### Problem
When nesting multiple blueprints where one or more nested blueprints declare \`url_prefix=""\`, the prefix calculation logic enters an infinite loop if parent and child share the same reference.

### Fix
Ensure cycle detection is performed during \`register_blueprint\` before prefix concatenation.`,
        changedFiles: [
          {
            path: 'src/flask/blueprints.py',
            status: 'modified',
            additions: 9,
            deletions: 2,
          },
        ],
        totalAdditions: 9,
        totalDeletions: 2,
      },
      {
        id: 'flask-4911',
        number: 4911,
        title: 'Draft: Support async generators in response streaming with ASGI adapters',
        author: 'pgjones',
        sourceBranch: 'async-stream-response',
        targetBranch: 'main',
        baseCommit: 'd5c21f0a82e75e5eb461b203498a964e52b2ef81',
        headCommit: '9c5812e9b177894318c645bc88ef7e02319984bc',
        updatedAt: '2026-10-31T08:15:00Z',
        createdAt: '2026-10-30T20:00:00Z',
        isDraft: true,
        htmlUrl: 'https://github.com/pallets/flask/pull/4911',
        description: `WIP: Explore yielding from async generators directly in response generators when running under Quart or ASGI wrappers. Not yet ready for review.`,
        changedFiles: [
          {
            path: 'src/flask/helpers.py',
            status: 'modified',
            additions: 42,
            deletions: 8,
          },
        ],
        totalAdditions: 42,
        totalDeletions: 8,
      },
    ],
  },
  'psf/requests': {
    repo: {
      id: 'psf/requests',
      owner: 'psf',
      name: 'requests',
      fullName: 'psf/requests',
      url: 'https://github.com/psf/requests',
      defaultBranch: 'main',
      isPrivate: false,
      connectedAt: new Date().toISOString(),
    },
    prs: [
      {
        id: 'requests-6214',
        number: 6214,
        title: 'Disallow conflicting Content-Length and Transfer-Encoding headers per RFC 7230',
        author: 'sigmavirus24',
        sourceBranch: 'rfc7230-chunked-header',
        targetBranch: 'main',
        baseCommit: 'b677a284687d6bb8b50dfbfa4604e2d31e9c565c',
        headCommit: 'c189b292e071e6be1c02ff4e715201c183cf9b44',
        updatedAt: '2026-10-27T10:14:00Z',
        createdAt: '2026-10-25T16:20:00Z',
        isDraft: false,
        htmlUrl: 'https://github.com/psf/requests/pull/6214',
        description: `### Summary
RFC 7230 Section 3.3.3 specifies that if a message is received with both a Transfer-Encoding header field and a Content-Length header field, the Content-Length must be removed or ignored.

Currently, \`requests\` sends both if configured via custom headers, which triggers proxy desync vulnerabilities on HTTP/1.1 connections.

### Proposed Solution
Strip Content-Length whenever \`chunked\` Transfer-Encoding is set.`,
        changedFiles: [
          {
            path: 'requests/models.py',
            status: 'modified',
            additions: 8,
            deletions: 2,
          },
          {
            path: 'tests/test_requests.py',
            status: 'modified',
            additions: 19,
            deletions: 0,
          },
        ],
        totalAdditions: 27,
        totalDeletions: 2,
      },
    ],
  },
};

export function parseRepositoryInput(input: string): { owner: string; name: string } | null {
  const trimmed = input.trim();
  if (!trimmed) return null;

  // Accept https://github.com/owner/repo or http://github.com/owner/repo
  const urlMatch = trimmed.match(/^https?:\/\/github\.com\/([A-Za-z0-9_.-]+)\/([A-Za-z0-9_.-]+?)(?:\.git|\/)?$/i);
  if (urlMatch) {
    return { owner: urlMatch[1], name: urlMatch[2] };
  }

  // Accept owner/repo
  const slashMatch = trimmed.match(/^([A-Za-z0-9_.-]+)\/([A-Za-z0-9_.-]+)$/);
  if (slashMatch) {
    return { owner: slashMatch[1], name: slashMatch[2] };
  }

  return null;
}

export async function devConnectRepository(
  input: string,
): Promise<RepositoryConnectionResult> {
  if (typeof process !== 'undefined' && process.env?.NODE_ENV !== 'test') {
    await new Promise((r) => setTimeout(r, 250));
  }

  const parsed = parseRepositoryInput(input);
  if (!parsed) {
    throw new Error('Unsupported repository URL. Please enter "owner/repository" or a valid "https://github.com/owner/repository" URL.');
  }

  const fullName = `${parsed.owner}/${parsed.name}`.toLowerCase();

  // If known preset, return it
  if (KNOWN_REPOSITORIES[fullName]) {
    return {
      repository: KNOWN_REPOSITORIES[fullName].repo,
      notice: 'Connected via Development Adapter (preset test fixtures available)',
    };
  }

  // Otherwise synthesize a valid repository representation
  const repo: ConnectedRepository = {
    id: fullName,
    owner: parsed.owner,
    name: parsed.name,
    fullName: `${parsed.owner}/${parsed.name}`,
    url: `https://github.com/${parsed.owner}/${parsed.name}`,
    defaultBranch: 'main',
    isPrivate: false,
    connectedAt: new Date().toISOString(),
  };

  return {
    repository: repo,
    notice: 'Connected via Development Adapter (demonstration repository)',
  };
}

export async function devFetchPullRequests(
  repoId: string,
): Promise<PullRequest[]> {
  if (typeof process !== 'undefined' && process.env?.NODE_ENV !== 'test') {
    await new Promise((r) => setTimeout(r, 200));
  }

  const normalized = repoId.toLowerCase().replace('https://github.com/', '').replace(/\/$/, '');
  if (KNOWN_REPOSITORIES[normalized]) {
    return KNOWN_REPOSITORIES[normalized].prs.map((p) => ({
      id: p.id,
      number: p.number,
      title: p.title,
      author: p.author,
      sourceBranch: p.sourceBranch,
      targetBranch: p.targetBranch,
      baseCommit: p.baseCommit,
      headCommit: p.headCommit,
      updatedAt: p.updatedAt,
      createdAt: p.createdAt,
      isDraft: p.isDraft,
      htmlUrl: p.htmlUrl,
    }));
  }

  // Generic fallback PRs for custom repositories
  return [
    {
      id: `${normalized}-101`,
      number: 101,
      title: 'Fix edge case with null arguments in configuration loader',
      author: 'contributor-1',
      sourceBranch: 'fix/null-config',
      targetBranch: 'main',
      baseCommit: 'a1b2c3d4e5f60718293a4b5c6d7e8f9012345678',
      headCommit: 'b2c3d4e5f60718293a4b5c6d7e8f90123456789a',
      updatedAt: new Date().toISOString(),
      createdAt: new Date(Date.now() - 86400000 * 2).toISOString(),
      isDraft: false,
      htmlUrl: `https://github.com/${normalized}/pull/101`,
    },
    {
      id: `${normalized}-102`,
      number: 102,
      title: 'Validate input boundaries in data ingestion pipeline',
      author: 'contributor-2',
      sourceBranch: 'feat/validation',
      targetBranch: 'main',
      baseCommit: 'a1b2c3d4e5f60718293a4b5c6d7e8f9012345678',
      headCommit: 'c3d4e5f60718293a4b5c6d7e8f90123456789a0b',
      updatedAt: new Date(Date.now() - 3600000 * 4).toISOString(),
      createdAt: new Date(Date.now() - 86400000 * 5).toISOString(),
      isDraft: false,
      htmlUrl: `https://github.com/${normalized}/pull/102`,
    },
  ];
}

export async function devFetchPullRequestDetail(
  repoId: string,
  prNumber: number,
): Promise<PullRequestDetail> {
  if (typeof process !== 'undefined' && process.env?.NODE_ENV !== 'test') {
    await new Promise((r) => setTimeout(r, 200));
  }

  const normalized = repoId.toLowerCase().replace('https://github.com/', '').replace(/\/$/, '');
  const entry = KNOWN_REPOSITORIES[normalized];
  if (entry) {
    const pr = entry.prs.find((p) => p.number === prNumber);
    if (pr) return pr;
  }

  return {
    id: `${normalized}-${prNumber}`,
    number: prNumber,
    title: `Pull Request #${prNumber}`,
    author: 'maintainer',
    sourceBranch: `feature/pr-${prNumber}`,
    targetBranch: 'main',
    baseCommit: 'a1b2c3d4e5f60718293a4b5c6d7e8f9012345678',
    headCommit: 'b2c3d4e5f60718293a4b5c6d7e8f90123456789a',
    updatedAt: new Date().toISOString(),
    createdAt: new Date().toISOString(),
    isDraft: false,
    htmlUrl: `https://github.com/${normalized}/pull/${prNumber}`,
    description: `Sample PR description for #${prNumber}.\n\nContains technical claims regarding repository behavior.`,
    changedFiles: [
      {
        path: 'src/main.py',
        status: 'modified',
        additions: 12,
        deletions: 3,
      },
      {
        path: 'tests/test_main.py',
        status: 'modified',
        additions: 25,
        deletions: 0,
      },
    ],
    totalAdditions: 37,
    totalDeletions: 3,
  };
}
