import { useState } from 'react';
import { ConnectedRepository, PullDetail } from '../../types/repository';
import { PRStatusBadge } from '../common/StatusBadge';
import { SafeMarkdown } from '../common/SafeMarkdown';
import {
  IconAlertTriangle,
  IconArrowLeft,
  IconClock,
  IconExternalLink,
  IconGitCommit,
  IconPlay,
  IconRefresh,
} from '../common/Icons';

interface PullRequestDetailsProps {
  repository: ConnectedRepository;
  pr: PullDetail;
  isSubmitting: boolean;
  onBackToInbox: () => void;
  onStartAnalysis: (prNumber: number) => void;
  onReopenAnalysis: (analysisId: string) => void;
}

export function PullRequestDetails({
  repository,
  pr,
  isSubmitting,
  onBackToInbox,
  onStartAnalysis,
  onReopenAnalysis,
}: PullRequestDetailsProps) {
  const [activeTab, setActiveTab] = useState<'overview' | 'history'>('overview');

  const latestHistory = pr.history && pr.history.length > 0 ? pr.history[0] : null;
  const isOutdated = Boolean(latestHistory?.outdated);
  const hasAnalysis = Boolean(latestHistory);

  return (
    <div className="pr-detail-container">
      {/* Top back navigation */}
      <nav className="detail-top-nav">
        <button
          type="button"
          className="btn-back"
          onClick={onBackToInbox}
          aria-label="Back to pull request inbox"
        >
          <IconArrowLeft size={14} />
          <span>Back to PR Inbox</span>
        </button>
      </nav>

      {/* Main PR Header */}
      <header className="pr-detail-header card">
        <div className="header-meta-row">
          <div className="header-title-wrap">
            <span className="pr-number-tag">#{pr.number}</span>
            <h2 className="pr-detail-title">{pr.title}</h2>
            {pr.draft && <span className="badge badge-draft">Draft</span>}
          </div>

          <div className="header-actions">
            <a
              href={pr.url}
              target="_blank"
              rel="noopener noreferrer"
              className="btn btn-secondary btn-sm"
              title="Open pull request on GitHub"
            >
              <IconExternalLink size={14} />
              <span>GitHub PR</span>
            </a>

            <button
              type="button"
              className="btn btn-primary"
              onClick={() => onStartAnalysis(pr.number)}
              disabled={isSubmitting}
            >
              {isSubmitting ? (
                <IconRefresh size={14} className="spin" />
              ) : (
                <IconPlay size={14} />
              )}
              <span>
                {isOutdated
                  ? 'Analyse latest revision'
                  : hasAnalysis
                  ? 'Re-analyse PR'
                  : 'Analyse PR'}
              </span>
            </button>
          </div>
        </div>

        {/* Sub-header branches and metadata */}
        <div className="pr-branches-row">
          <span className="repo-name-label">
            <strong>{repository.full_name}</strong>
          </span>
          <span className="author-line">
            Opened by <strong>{pr.author}</strong>
          </span>
          <span className="branch-pair">
            <code className="branch-badge">{pr.base_branch}</code>
            <span className="branch-arrow">&larr;</span>
            <code className="branch-badge">{pr.head_branch}</code>
          </span>
          <span className="pr-updated-time">
            <IconClock size={12} />
            <span>Updated {new Date(pr.updated_at).toLocaleDateString()}</span>
          </span>
        </div>

        {/* Outdated analysis warning banner */}
        {isOutdated && latestHistory && (
          <div className="callout callout-warning mt-3" role="alert">
            <IconAlertTriangle size={16} className="callout-icon" />
            <div className="callout-content">
              <strong>Outdated — this PR has new commits since this investigation:</strong> Previous
              analysis was performed against PR head commit <code>{latestHistory.context.head_sha?.slice(0, 10)}</code>.
              The current PR head is <code>{pr.head_sha.slice(0, 10)}</code>.
              <div className="callout-actions mt-2 flex gap-2">
                <button
                  type="button"
                  className="btn btn-sm btn-secondary"
                  onClick={() => onReopenAnalysis(latestHistory.id)}
                >
                  View earlier analysis ({latestHistory.context.head_sha?.slice(0, 7)})
                </button>
                <button
                  type="button"
                  className="btn btn-sm btn-primary"
                  onClick={() => onStartAnalysis(pr.number)}
                  disabled={isSubmitting}
                >
                  Analyse latest revision
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Previous analysis button if up to date */}
        {!isOutdated && latestHistory && (
          <div className="analysis-status-strip mt-3">
            <div className="status-label-group">
              <span className="status-label">Latest Investigation:</span>
              <PRStatusBadge
                status={
                  latestHistory.stage === 'complete'
                    ? 'complete'
                    : latestHistory.stage === 'error'
                    ? 'failed'
                    : 'analysing'
                }
              />
            </div>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => onReopenAnalysis(latestHistory.id)}
            >
              Open Active Investigation Workspace
            </button>
          </div>
        )}

        {/* Pinned Revisions Comparison Context Card (Backend-Resolved!) */}
        <div className="revisions-context-box">
          <div className="context-item">
            <span className="context-label">
              <IconGitCommit size={13} />
              <span>Base Comparison Revision</span>
            </span>
            <code className="commit-hash" title={pr.base_sha}>
              {pr.base_sha}
            </code>
            <span className="context-desc">Pre-fix baseline snapshot (resolved by backend)</span>
          </div>

          <div className="context-divider">&rarr;</div>

          <div className="context-item">
            <span className="context-label">
              <IconGitCommit size={13} />
              <span>PR Head Revision</span>
            </span>
            <code className="commit-hash" title={pr.head_sha}>
              {pr.head_sha}
            </code>
            <span className="context-desc">Proposed change snapshot ({pr.head_repository})</span>
          </div>
        </div>
      </header>

      {/* Tabs: Description vs Investigation History */}
      <div className="detail-tabs" role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'overview'}
          className={`detail-tab ${activeTab === 'overview' ? 'active' : ''}`}
          onClick={() => setActiveTab('overview')}
        >
          Description &amp; Metadata
          {(pr.additions !== null || pr.deletions !== null) && (
            <span className="diff-stats ml-2">
              <span className="stat-add">+{pr.additions ?? 0}</span>
              <span className="stat-del">-{pr.deletions ?? 0}</span>
            </span>
          )}
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'history'}
          className={`detail-tab ${activeTab === 'history' ? 'active' : ''}`}
          onClick={() => setActiveTab('history')}
        >
          Investigation History ({pr.history ? pr.history.length : 0})
        </button>
      </div>

      {/* Tab Panels */}
      <div className="detail-panel card">
        {activeTab === 'overview' && (
          <div className="pr-description-panel">
            <div className="pr-stats-row mb-3 pb-3 border-b border-subtle flex gap-4 text-sm text-secondary">
              <span>Changed Files: <strong>{pr.changed_files ?? 'N/A'}</strong></span>
              <span>Source Repository: <code>{pr.head_repository}</code></span>
            </div>
            <h3 className="panel-title sr-only">PR Description</h3>
            <SafeMarkdown content={pr.body || '(No description provided for this pull request.)'} />
          </div>
        )}

        {activeTab === 'history' && (
          <div className="pr-history-panel">
            {(!pr.history || pr.history.length === 0) ? (
              <p className="text-muted text-sm py-4 text-center">
                No previous NoBluff investigations found for PR #{pr.number}. Click &ldquo;Analyse PR&rdquo; to start.
              </p>
            ) : (
              <div className="history-list flex flex-col gap-3">
                {pr.history.map((h) => (
                  <div key={h.id} className="history-entry-card p-3 border border-subtle rounded flex justify-between items-center">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-semibold">{h.id}</span>
                        <span className={`badge badge-${h.stage === 'complete' ? 'supported' : 'neutral'}`}>
                          {h.stage}
                        </span>
                        {h.outdated && (
                          <span className="badge badge-inconclusive">Outdated</span>
                        )}
                      </div>
                      <div className="text-xs text-muted mt-1 flex gap-3">
                        <span>Head: <code>{h.context?.head_sha?.slice(0, 10)}</code></span>
                        <span>Created: {new Date(h.created_at).toLocaleString()}</span>
                      </div>
                    </div>
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      onClick={() => onReopenAnalysis(h.id)}
                    >
                      Open Report
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
