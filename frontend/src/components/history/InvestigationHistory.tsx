import { InvestigationRecord } from '../../types/repository';
import { getExportUrl } from '../../api/client';
import {
  IconClock,
  IconDownload,
  IconFileCode,
  IconInfo,
  IconRefresh,
} from '../common/Icons';

interface InvestigationHistoryProps {
  investigations: InvestigationRecord[];
  isLoading?: boolean;
  onRefresh?: () => void;
  onOpenReport: (id: string) => void;
}

export function InvestigationHistory({
  investigations,
  isLoading = false,
  onRefresh,
  onOpenReport,
}: InvestigationHistoryProps) {
  if (isLoading && investigations.length === 0) {
    return (
      <div className="history-empty card">
        <IconRefresh size={28} className="spin text-muted" />
        <h4 className="empty-title">Loading investigations...</h4>
        <p className="empty-desc">Querying persisted records from SQLite workspace.</p>
      </div>
    );
  }

  if (investigations.length === 0) {
    return (
      <div className="history-empty card">
        <IconClock size={28} className="text-muted" />
        <h4 className="empty-title">No persisted investigations</h4>
        <p className="empty-desc">
          Analyses run for connected repositories are persisted to backend SQLite storage and will appear here across restarts.
        </p>
      </div>
    );
  }

  return (
    <div className="history-container">
      <div className="history-header flex justify-between items-center">
        <div>
          <h3 className="section-heading">Investigation History</h3>
          <p className="section-lead">
            Durable investigations stored in SQLite. Completed reports remain inspectable across browser and server restarts.
          </p>
        </div>
        {onRefresh && (
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={onRefresh}
            disabled={isLoading}
          >
            <IconRefresh size={12} className={isLoading ? 'spin' : ''} />
            <span>Refresh History</span>
          </button>
        )}
      </div>

      <div className="callout callout-info mb-4">
        <IconInfo size={16} className="callout-icon" />
        <div className="callout-content">
          <strong>Durable SQLite Workspace:</strong> Investigation records and context
          are stored server-side. Pinned snapshots and JSON/Markdown downloads remain available
          after server restarts.
        </div>
      </div>

      <div className="history-list">
        {investigations.map((item) => {
          const prNumber = item.context?.pr_number as number | undefined;
          const prTitle = item.context?.title as string | undefined;

          return (
            <div key={item.id} className="history-card">
              <div className="history-main-info">
                <div className="history-title-row">
                  <span className="history-id">
                    ID: <code>{item.id}</code>
                  </span>
                  {prNumber && (
                    <span className="badge badge-subtle">
                      PR #{prNumber}
                    </span>
                  )}
                  <span
                    className={`badge badge-${
                      item.stage === 'complete'
                        ? 'supported'
                        : item.stage === 'error'
                        ? 'contradicted'
                        : 'neutral'
                    }`}
                  >
                    {item.stage}
                  </span>
                </div>

                {prTitle && (
                  <div className="history-pr-title">{prTitle}</div>
                )}

                <div className="history-meta-row">
                  <span>Repo: <strong>{item.repository.replace('https://github.com/', '')}</strong></span>
                  <span>Revision: <code>{item.revision.slice(0, 10)}</code></span>
                  {item.comparison_revision && (
                    <span>
                      Head: <code>{item.comparison_revision.slice(0, 10)}</code>
                    </span>
                  )}
                  <span className="text-muted">
                    {new Date(item.created_at).toLocaleDateString()} {new Date(item.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>
              </div>

              <div className="history-actions">
                <button
                  type="button"
                  className="btn btn-primary btn-sm"
                  onClick={() => onOpenReport(item.id)}
                >
                  Open Report
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
          );
        })}
      </div>
    </div>
  );
}
