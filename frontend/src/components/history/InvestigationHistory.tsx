import { StoredInvestigation } from '../../api/storage';
import { getExportUrl } from '../../api/client';
import {
  IconClock,
  IconDownload,
  IconFileCode,
  IconInfo,
} from '../common/Icons';

interface InvestigationHistoryProps {
  investigations: StoredInvestigation[];
  onOpenReport: (id: string) => void;
}

export function InvestigationHistory({
  investigations,
  onOpenReport,
}: InvestigationHistoryProps) {
  if (investigations.length === 0) {
    return (
      <div className="history-empty card">
        <IconClock size={28} className="text-muted" />
        <h4 className="empty-title">No recent investigations</h4>
        <p className="empty-desc">
          Analyses run in this browser session will appear here for quick reopening and report export.
        </p>
      </div>
    );
  }

  return (
    <div className="history-container">
      <div className="history-header">
        <h3 className="section-heading">Investigation History</h3>
        <p className="section-lead">
          Recent analyses tracked in this browser session. Server-side durable history
          is planned in the backend persistence handoff.
        </p>
      </div>

      <div className="callout callout-info mb-4">
        <IconInfo size={16} className="callout-icon" />
        <div className="callout-content">
          <strong>Backend Storage Note:</strong> The current NoBluff backend stores
          reports in memory (bounded to 100 per server process). Reports reset when the
          backend restarts.
        </div>
      </div>

      <div className="history-list">
        {investigations.map((item) => (
          <div key={item.id} className="history-card">
            <div className="history-main-info">
              <div className="history-title-row">
                <span className="history-id">
                  ID: <code>{item.id}</code>
                </span>
                {item.prNumber && (
                  <span className="badge badge-subtle">
                    PR #{item.prNumber}
                  </span>
                )}
                <span className={`badge badge-${item.stage === 'complete' ? 'supported' : 'neutral'}`}>
                  {item.stage}
                </span>
              </div>

              {item.prTitle && (
                <div className="history-pr-title">{item.prTitle}</div>
              )}

              <div className="history-meta-row">
                <span>Repo: <strong>{item.repository}</strong></span>
                <span>Revision: <code>{item.revision.slice(0, 10)}</code></span>
                {item.comparison_revision && (
                  <span>
                    Comparison: <code>{item.comparison_revision.slice(0, 10)}</code>
                  </span>
                )}
                <span className="text-muted">
                  {new Date(item.createdAt).toLocaleDateString()} {new Date(item.createdAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>

              <div className="history-counts-row">
                <span className="count-pill">
                  {item.claimCount} {item.claimCount === 1 ? 'claim' : 'claims'}
                </span>
                <span className="count-pill">
                  {item.findingCount} {item.findingCount === 1 ? 'finding' : 'findings'}
                </span>
                <span className="count-pill">
                  {item.executionCount} {item.executionCount === 1 ? 'run' : 'runs'}
                </span>
              </div>
            </div>

            <div className="history-actions">
              <button
                type="button"
                className="btn btn-primary btn-sm"
                onClick={() => onOpenReport(item.id)}
              >
                Reopen Workspace
              </button>

              <div className="export-btn-group">
                <a
                  href={getExportUrl(item.id, 'json')}
                  download={`nobluff-${item.id}.json`}
                  className="btn btn-secondary btn-sm"
                  title="Download backend report as JSON"
                >
                  <IconDownload size={13} />
                  <span>JSON</span>
                </a>
                <a
                  href={getExportUrl(item.id, 'markdown')}
                  download={`nobluff-${item.id}.md`}
                  className="btn btn-secondary btn-sm"
                  title="Download backend report as Markdown"
                >
                  <IconFileCode size={13} />
                  <span>Markdown</span>
                </a>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
