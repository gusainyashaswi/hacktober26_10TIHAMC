import {
  ConnectedRepository,
  PullDetail,
  PullSummary,
} from '../types/repository';

export interface RepositoryConnectionResult {
  repository: ConnectedRepository;
  notice: string;
}

// Built-in curated open-source development fixtures for offline dev testing
const KNOWN_REPOSITORIES: Record<
  string,
  { repo: ConnectedRepository; prs: PullDetail[] }
> = {
  'pallets/flask': {
    repo: {
      id: 991,
      full_name: 'pallets/flask',
      url: 'https://github.com/pallets/flask',
      default_branch: 'main',
      connected_at: new Date().toISOString(),
    },
    prs: [
      {
        number: 4892,
        title:
          'Fix request argument parsing when query string contains malformed percent-encoded sequences',
        author: 'untitaker',
        url: 'https://github.com/pallets/flask/pull/4892',
        state: 'open',
        draft: false,
        updated_at: '2026-10-28T14:30:00Z',
        head_sha: 'f849a64e1c28c89b2751f7253507d62058fa72da',
        base_sha: 'd5c21f0a82e75e5eb461b203498a964e52b2ef81',
        head_branch: 'fix-malformed-query-encoding',
        base_branch: 'main',
        head_repository: 'https://github.com/untitaker/flask',
        body: `### Description\nWhen parsing malformed query strings with invalid percent-encodings like \`%ZZ\` or truncated sequences like \`%A\`, \`urllib.parse.parse_qs\` raises a \`UnicodeDecodeError\` or \`ValueError\` instead of treating it as an invalid query parameter.\n\nUnder certain WSGI gateways, this results in an unhandled 500 error instead of a graceful 400 Bad Request.\n\n### Proposed Changes\n- In \`src/flask/wrappers.py\`, wrap query string unquoting with a try/except block.\n- Convert unquote parse errors to \`BadRequestKeyError\` or empty parameter fallback.\n- Added pytest reproduction in \`tests/test_basic.py\`.`,
        additions: 36,
        deletions: 4,
        changed_files: 2,
        merged: false,
        history: [],
      },
      {
        number: 4904,
        title:
          'Prevent recursive loop when nesting blueprints with empty url_prefix',
        author: 'davidism',
        url: 'https://github.com/pallets/flask/pull/4904',
        state: 'open',
        draft: false,
        updated_at: '2026-10-30T18:45:00Z',
        head_sha: 'a93b58913d317072a24c0840b2a7587ea0b75a41',
        base_sha: 'e28b8a53173d6b057c32bfdb07f5d6ee4680ea3b',
        head_branch: 'blueprint-prefix-recursion',
        base_branch: 'main',
        head_repository: 'https://github.com/pallets/flask',
        body: `### Problem\nWhen nesting multiple blueprints where one or more nested blueprints declare \`url_prefix=""\`, the prefix calculation logic enters an infinite loop if parent and child share the same reference.\n\n### Fix\nEnsure cycle detection is performed during \`register_blueprint\` before prefix concatenation.`,
        additions: 9,
        deletions: 2,
        changed_files: 1,
        merged: false,
        history: [],
      },
    ],
  },
};

export function parseRepositoryInput(
  input: string,
): { owner: string; name: string } | null {
  const trimmed = input.trim();
  if (!trimmed) return null;

  const urlMatch = trimmed.match(
    /^https?:\/\/github\.com\/([A-Za-z0-9_.-]+)\/([A-Za-z0-9_.-]+?)(?:\.git|\/)?$/i,
  );
  if (urlMatch) {
    return { owner: urlMatch[1], name: urlMatch[2] };
  }

  const slashMatch = trimmed.match(/^([A-Za-z0-9_.-]+)\/([A-Za-z0-9_.-]+)$/);
  if (slashMatch) {
    return { owner: slashMatch[1], name: slashMatch[2] };
  }

  return null;
}

export async function devConnectRepository(
  input: string,
): Promise<RepositoryConnectionResult> {
  const parsed = parseRepositoryInput(input);
  if (!parsed) {
    throw new Error(
      'Unsupported repository format. Please enter "owner/repository" or a valid "https://github.com/owner/repository" URL.',
    );
  }

  const fullName = `${parsed.owner}/${parsed.name}`.toLowerCase();
  if (KNOWN_REPOSITORIES[fullName]) {
    return {
      repository: KNOWN_REPOSITORIES[fullName].repo,
      notice: 'Connected via Isolated Development Adapter (Fixture)',
    };
  }

  return {
    repository: {
      id: Math.floor(Math.random() * 9000) + 1000,
      full_name: `${parsed.owner}/${parsed.name}`,
      url: `https://github.com/${parsed.owner}/${parsed.name}`,
      default_branch: 'main',
      connected_at: new Date().toISOString(),
    },
    notice: 'Connected via Isolated Development Adapter (Synthetic)',
  };
}

export async function devFetchPullRequests(
  repoFullName: string,
): Promise<PullSummary[]> {
  const normalized = repoFullName.toLowerCase().replace('https://github.com/', '').replace(/\/$/, '');
  if (KNOWN_REPOSITORIES[normalized]) {
    return KNOWN_REPOSITORIES[normalized].prs.map((p) => ({
      number: p.number,
      title: p.title,
      author: p.author,
      url: p.url,
      state: p.state,
      draft: p.draft,
      updated_at: p.updated_at,
      head_sha: p.head_sha,
      base_sha: p.base_sha,
      head_branch: p.head_branch,
      base_branch: p.base_branch,
    }));
  }

  return [
    {
      number: 101,
      title: 'Fix edge case with null arguments in configuration loader',
      author: 'contributor-1',
      url: `https://github.com/${normalized}/pull/101`,
      state: 'open',
      draft: false,
      updated_at: new Date().toISOString(),
      head_sha: 'b2c3d4e5f60718293a4b5c6d7e8f90123456789a',
      base_sha: 'a1b2c3d4e5f60718293a4b5c6d7e8f9012345678',
      head_branch: 'fix/null-config',
      base_branch: 'main',
    },
  ];
}

export async function devFetchPullRequestDetail(
  repoFullName: string,
  prNumber: number,
): Promise<PullDetail> {
  const normalized = repoFullName.toLowerCase().replace('https://github.com/', '').replace(/\/$/, '');
  const entry = KNOWN_REPOSITORIES[normalized];
  if (entry) {
    const pr = entry.prs.find((p) => p.number === prNumber);
    if (pr) return pr;
  }

  return {
    number: prNumber,
    title: `Pull Request #${prNumber}`,
    author: 'maintainer',
    url: `https://github.com/${normalized}/pull/${prNumber}`,
    state: 'open',
    draft: false,
    updated_at: new Date().toISOString(),
    head_sha: 'b2c3d4e5f60718293a4b5c6d7e8f90123456789a',
    base_sha: 'a1b2c3d4e5f60718293a4b5c6d7e8f9012345678',
    head_branch: `feature/pr-${prNumber}`,
    base_branch: 'main',
    head_repository: `https://github.com/${normalized}`,
    body: `Sample PR description for #${prNumber}.\n\nContains technical claims regarding repository behavior.`,
    additions: 12,
    deletions: 3,
    changed_files: 2,
    merged: false,
    history: [],
  };
}
