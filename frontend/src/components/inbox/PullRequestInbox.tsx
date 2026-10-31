import { useMemo, useState } from 'react';
import {
  ConnectedRepository,
  PullRequest,
  PRAnalysisStatus,
} from '../../types/repository';
import { PRStatusBadge } from '../common/StatusBadge';
import {
  IconAlertCircle,
  IconClock,
  IconExternalLink,
  IconGitPullRequest,
  IconRefresh,
  IconSearch,
} from '../common/Icons';
import { PRAnalysisRecord } from '../../api/storage';

interface PullRequestInboxProps {
  repository: ConnectedRepository;
  pullRequests: PullRequest[];
  analysisMap: Record<number, PRAnalysisRecord>;
  isLoading: boolean;
  error: string | null;
  lastRefreshed: Date | null;
  onRefresh: () => void;
  onSelectPR: (pr: PullRequest) => void;
  onSwitchRepository: () => void;
  isDevMode: boolean;
}

export function PullRequestInbox({
  repository,
  pullRequests,
  analysisMap,
  isLoading,
  error,
  lastRefreshed,
  onRefresh,
  onSelectPR,
  onSwitchRepository,
  isDevMode,
}: PullRequestInboxProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'needs_analysis' | 'complete'>('all');

  // Compute effective analysis state for each PR
  const enrichedPRs = useMemo(() => {
    return pullRequests.map((pr) => {
      const record = analysisMap[pr.number];
      let analysisState: PRAnalysisStatus = 'not_analysed';

      if (record) {
        if (record.analysedHeadCommit && record.analysedHeadCommit !== pr.headCommit) {
          analysisState = 'outdated';
        } else {
          analysisState = record.status;
        }
      }

      return {
        ...pr,
        analysisState,
      };
    });
  }, [pullRequests, analysisMap]);

  // Filtered and searched PRs
  const filteredPRs = useMemo(() => {
    return enrichedPRs.filter((pr) => {
      // Search
      const query = searchQuery.trim().toLowerCase();
      if (query) {
        const matchesNumber = pr.number.toString().includes(query);
        const matchesTitle = pr.title.toLowerCase().includes(query);
        const matchesAuthor = pr.author.toLowerCase().includes(query);
        if (!matchesNumber && !matchesTitle && !matchesAuthor) {
          return false;
        }
      }

      // Filter
      if (statusFilter === 'needs_analysis') {
        return (
          pr.analysisState === 'not_analysed' ||
          pr.analysisState === 'outdated' ||
          pr.analysisState === 'failed'
        );
      }
      if (statusFilter === 'complete') {
        return pr.analysisState === 'complete';
      }

      return true;
    });
  }, [enrichedPRs, searchQuery, statusFilter]);

  const formatRelativeTime = (isoString: string) => {
    try {
      const date = new Date(isoString);
      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
      const diffDays = Math.floor(diffHours / 24);

      if (diffDays > 0) return `${diffDays}d ago`;
      if (diffHours > 0) return `${diffHours}h ago`;
      return 'just now';
    } catch {
      return isoString;
    }
  };

  return (
    <div className="inbox-container">
      {/* Header and metadata */}
      <header className="inbox-header">
        <div className="inbox-header-title-row">
          <div className="inbox-repo-badge">
            <span className="repo-owner">{repository.owner}</span>
            <span className="repo-divider">/</span>
            <span className="repo-name">{repository.name}</span>
            <button
              type="button"
              className="btn-switch-repo"
              onClick={onSwitchRepository}
              title="Switch or connect another repository"
            >
              Switch
            </button>
          </div>

          <div className="inbox-header-actions">
            {lastRefreshed && (
              <span className="last-refreshed">
                <IconClock size={12} />
                <span>Updated {lastRefreshed.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
              </span>
            )}
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={onRefresh}
              disabled={isLoading}
              title="Refresh pull request inbox"
            >
              <IconRefresh size={14} className={isLoading ? 'spin' : ''} />
              <span>Refresh</span>
            </button>
          </div>
        </div>

        {/* Development mode indicator banner */}
        {isDevMode && (
          <div className="dev-adapter-banner" role="note">
            <span className="dev-adapter-tag">Dev Adapter</span>
            <span>
              Showing open-source test fixtures for <strong>{repository.fullName}</strong>. Live GitHub PR polling requires backend GitHub App integration.
            </span>
          </div>
        )}

        {/* Filter bar and search */}
        <div className="inbox-controls">
          <div className="search-wrap">
            <IconSearch size={14} className="search-icon" />
            <input
              type="search"
              className="search-input"
              placeholder="Filter by title, author, or #..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              aria-label="Filter pull requests"
            />
          </div>

          <div className="filter-tabs" role="tablist" aria-label="PR analysis filter">
            <button
              type="button"
              role="tab"
              aria-selected={statusFilter === 'all'}
              className={`filter-tab ${statusFilter === 'all' ? 'active' : ''}`}
              onClick={() => setStatusFilter('all')}
            >
              All Open ({enrichedPRs.length})
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={statusFilter === 'needs_analysis'}
              className={`filter-tab ${statusFilter === 'needs_analysis' ? 'active' : ''}`}
              onClick={() => setStatusFilter('needs_analysis')}
            >
              Needs Analysis (
              {
                enrichedPRs.filter(
                  (p) =>
                    p.analysisState === 'not_analysed' ||
                    p.analysisState === 'outdated' ||
                    p.analysisState === 'failed',
                ).length
              }
              )
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={statusFilter === 'complete'}
              className={`filter-tab ${statusFilter === 'complete' ? 'active' : ''}`}
              onClick={() => setStatusFilter('complete')}
            >
              Analysed ({enrichedPRs.filter((p) => p.analysisState === 'complete').length})
            </button>
          </div>
        </div>
      </header>

      {/* Main Inbox List */}
      <main className="inbox-list-wrap">
        {isLoading && pullRequests.length === 0 && (
          <div className="empty-state" role="status">
            <IconRefresh size={24} className="spin text-muted" />
            <p className="empty-title">Fetching open pull requests...</p>
            <p className="empty-desc">Querying repository metadata and commit SHAs.</p>
          </div>
        )}

        {error && (
          <div className="callout callout-error" role="alert">
            <IconAlertCircle size={16} className="callout-icon" />
            <div className="callout-content">
              <strong>Failed to fetch pull requests:</strong> {error}
              <button
                type="button"
                className="btn btn-sm btn-secondary mt-2"
                onClick={onRefresh}
              >
                Retry
              </button>
            </div>
          </div>
        )}

        {!isLoading && !error && pullRequests.length === 0 && (
          <div className="empty-state">
            <IconGitPullRequest size={28} className="text-muted" />
            <p className="empty-title">No open pull requests</p>
            <p className="empty-desc">
              There are currently no open pull requests in {repository.fullName}.
            </p>
          </div>
        )}

        {!isLoading && pullRequests.length > 0 && filteredPRs.length === 0 && (
          <div className="empty-state">
            <IconSearch size={24} className="text-muted" />
            <p className="empty-title">No matching pull requests</p>
            <p className="empty-desc">
              No open PRs matched your search query &ldquo;{searchQuery}&rdquo;.
            </p>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => {
                setSearchQuery('');
                setStatusFilter('all');
              }}
            >
              Clear filters
            </button>
          </div>
        )}

        {filteredPRs.length > 0 && (
          <div className="pr-table" role="table" aria-label="Pull requests">
            <div className="pr-table-header" role="row">
              <span className="col-pr">Pull Request</span>
              <span className="col-branch">Branches</span>
              <span className="col-status">NoBluff Status</span>
              <span className="col-time">Updated</span>
              <span className="col-action">Action</span>
            </div>

            {filteredPRs.map((pr) => (
              <div
                key={pr.id}
                className="pr-row"
                role="row"
                tabIndex={0}
                onClick={() => onSelectPR(pr)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    onSelectPR(pr);
                  }
                }}
              >
                <div className="col-pr pr-meta">
                  <div className="pr-title-row">
                    <span className="pr-number">#{pr.number}</span>
                    <span className="pr-title">{pr.title}</span>
                    {pr.isDraft && <span className="badge badge-draft">Draft</span>}
                  </div>
                  <div className="pr-sub-row">
                    <span className="pr-author">opened by {pr.author}</span>
                    <a
                      href={pr.htmlUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="pr-github-link"
                      onClick={(e) => e.stopPropagation()}
                      title="Open PR on GitHub"
                      aria-label={`Open PR #${pr.number} on GitHub`}
                    >
                      <IconExternalLink size={12} />
                    </a>
                  </div>
                </div>

                <div className="col-branch pr-branch-info">
                  <code className="branch-name" title={pr.sourceBranch}>
                    {pr.sourceBranch}
                  </code>
                  <span className="branch-arrow">&rarr;</span>
                  <code className="branch-name" title={pr.targetBranch}>
                    {pr.targetBranch}
                  </code>
                </div>

                <div className="col-status">
                  <PRStatusBadge status={pr.analysisState || 'not_analysed'} />
                </div>

                <div className="col-time text-muted">
                  {formatRelativeTime(pr.updatedAt)}
                </div>

                <div className="col-action">
                  <button
                    type="button"
                    className="btn btn-sm btn-table-action"
                    onClick={(e) => {
                      e.stopPropagation();
                      onSelectPR(pr);
                    }}
                  >
                    Investigate
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
