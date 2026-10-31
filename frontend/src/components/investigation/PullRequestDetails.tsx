import { useState } from 'react';
import { ConnectedRepository, PullRequestDetail } from '../../types/repository';
import { PRStatusBadge } from '../common/StatusBadge';
import { SafeMarkdown } from '../common/SafeMarkdown';
import { PRAnalysisRecord } from '../../api/storage';
import {
  IconAlertTriangle,
  IconArrowLeft,
  IconClock,
  IconExternalLink,
  IconFileCode,
  IconGitCommit,
  IconPlay,
  IconRefresh,
} from '../common/Icons';

interface PullRequestDetailsProps {
  repository: ConnectedRepository;
  pr: PullRequestDetail;
  analysisRecord?: PRAnalysisRecord;
  isSubmitting: boolean;
  onBackToInbox: () => void;
  onStartAnalysis: () => void;
  onReopenAnalysis: (analysisId: string) => void;
}

export function PullRequestDetails({
  repository,
  pr,
  analysisRecord,
  isSubmitting,
  onBackToInbox,
  onStartAnalysis,
  onReopenAnalysis,
}: PullRequestDetailsProps) {
  const [activeTab, setActiveTab] = useState<'overview' | 'files'>('overview');

  const isOutdated =
    analysisRecord &&
    analysisRecord.analysedHeadCommit &&
    analysisRecord.analysedHeadCommit !== pr.headCommit;

  const hasAnalysis = Boolean(analysisRecord);

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
            {pr.isDraft && <span className="badge badge-draft">Draft</span>}
          </div>

          <div className="header-actions">
            <a
              href={pr.htmlUrl}
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
              onClick={onStartAnalysis}
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
            <strong>{repository.fullName}</strong>
          </span>
          <span className="author-line">
            Opened by <strong>{pr.author}</strong>
          </span>
          <span className="branch-pair">
            <code className="branch-badge">{pr.targetBranch}</code>
            <span className="branch-arrow">&larr;</span>
            <code className="branch-badge">{pr.sourceBranch}</code>
          </span>
          <span className="pr-updated-time">
            <IconClock size={12} />
            <span>Updated {new Date(pr.updatedAt).toLocaleDateString()}</span>
          </span>
        </div>

        {/* Outdated analysis warning banner */}
        {isOutdated && analysisRecord && (
          <div className="callout callout-warning mt-3" role="alert">
            <IconAlertTriangle size={16} className="callout-icon" />
            <div className="callout-content">
              <strong>PR head commit changed:</strong> A previous analysis was performed
              against revision <code>{analysisRecord.analysedHeadCommit.slice(0, 10)}</code>.
              The current PR head is <code>{pr.headCommit.slice(0, 10)}</code>.
              <div className="callout-actions mt-2">
                <button
                  type="button"
                  className="btn btn-sm btn-secondary"
                  onClick={() => onReopenAnalysis(analysisRecord.analysisId)}
                >
                  View earlier analysis
                </button>
                <button
                  type="button"
                  className="btn btn-sm btn-primary"
                  onClick={onStartAnalysis}
                >
                  Analyse latest revision
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Previous analysis button if up to date */}
        {!isOutdated && analysisRecord && (
          <div className="analysis-status-strip mt-3">
            <div className="status-label-group">
              <span className="status-label">NoBluff Analysis:</span>
              <PRStatusBadge status={analysisRecord.status} />
            </div>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => onReopenAnalysis(analysisRecord.analysisId)}
            >
              Open Active Investigation Workspace
            </button>
          </div>
        )}

        {/* Pinned Revisions Comparison Context Card */}
        <div className="revisions-context-box">
          <div className="context-item">
            <span className="context-label">
              <IconGitCommit size={13} />
              <span>Base Comparison Revision</span>
            </span>
            <code className="commit-hash" title={pr.baseCommit}>
              {pr.baseCommit}
            </code>
            <span className="context-desc">Pre-fix baseline snapshot</span>
          </div>

          <div className="context-divider">&rarr;</div>

          <div className="context-item">
            <span className="context-label">
              <IconGitCommit size={13} />
              <span>PR Head Revision</span>
            </span>
            <code className="commit-hash" title={pr.headCommit}>
              {pr.headCommit}
            </code>
            <span className="context-desc">Proposed change snapshot</span>
          </div>
        </div>
      </header>

      {/* Tabs: Description vs Changed Files */}
      <div className="detail-tabs" role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'overview'}
          className={`detail-tab ${activeTab === 'overview' ? 'active' : ''}`}
          onClick={() => setActiveTab('overview')}
        >
          Description
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'files'}
          className={`detail-tab ${activeTab === 'files' ? 'active' : ''}`}
          onClick={() => setActiveTab('files')}
        >
          Changed Files ({pr.changedFiles.length})
          <span className="diff-stats">
            <span className="stat-add">+{pr.totalAdditions}</span>
            <span className="stat-del">-{pr.totalDeletions}</span>
          </span>
        </button>
      </div>

      {/* Tab Panels */}
      <div className="detail-panel card">
        {activeTab === 'overview' && (
          <div className="pr-description-panel">
            <h3 className="panel-title sr-only">PR Description</h3>
            <SafeMarkdown content={pr.description} />
          </div>
        )}

        {activeTab === 'files' && (
          <div className="changed-files-panel">
            <div className="files-list">
              {pr.changedFiles.map((file, i) => (
                <div key={i} className="file-row">
                  <div className="file-name-col">
                    <IconFileCode size={14} className="text-secondary" />
                    <code className="file-path">{file.path}</code>
                    <span className={`badge badge-file-${file.status}`}>
                      {file.status}
                    </span>
                  </div>
                  <div className="file-diff-col">
                    <span className="stat-add">+{file.additions}</span>
                    <span className="stat-del">-{file.deletions}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
