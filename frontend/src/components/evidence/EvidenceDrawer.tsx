import { useEffect, useRef, useState } from 'react';
import { Evidence, ExecutionResult } from '../../types/analysis';
import {
  IconCheck,
  IconCopy,
  IconExternalLink,
  IconFileCode,
  IconTerminal,
  IconX,
} from '../common/Icons';

interface EvidenceDrawerProps {
  isOpen: boolean;
  evidence: Evidence | null;
  execution?: ExecutionResult | null;
  repositoryUrl?: string;
  onClose: () => void;
}

export function EvidenceDrawer({
  isOpen,
  evidence,
  execution,
  repositoryUrl,
  onClose,
}: EvidenceDrawerProps) {
  const [copied, setCopied] = useState(false);
  const drawerRef = useRef<HTMLDivElement>(null);

  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen || !evidence) return null;

  const isExecution = evidence.kind === 'execution';

  // Construct GitHub permalink if canonical url, commit and path exist
  const getGitHubPermalink = () => {
    if (!repositoryUrl || !evidence.revision || !evidence.path) return null;
    const cleanRepo = repositoryUrl.replace(/\.git$/, '').replace(/\/$/, '');
    const lines =
      evidence.start_line && evidence.end_line
        ? evidence.start_line === evidence.end_line
          ? `#L${evidence.start_line}`
          : `#L${evidence.start_line}-L${evidence.end_line}`
        : '';
    return `${cleanRepo}/blob/${evidence.revision}/${evidence.path}${lines}`;
  };

  const permalink = getGitHubPermalink();

  const handleCopyReference = () => {
    let textToCopy = '';
    if (isExecution) {
      textToCopy = `Execution Evidence [${evidence.id}] (Run: ${evidence.execution_id || 'unknown'}, Revision: ${evidence.revision})`;
    } else {
      textToCopy = `${evidence.path || 'unknown'}:${evidence.start_line || 1}-${evidence.end_line || 1} (${evidence.revision})`;
    }
    navigator.clipboard.writeText(textToCopy);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Split excerpt into lines with line numbers
  const excerptLines = evidence.excerpt.split('\n');
  const startLineNum = evidence.start_line || 1;

  return (
    <div
      className="drawer-backdrop"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="drawer-title"
    >
      <div
        className="evidence-drawer"
        ref={drawerRef}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Drawer Header */}
        <header className="drawer-header">
          <div className="drawer-title-row">
            {isExecution ? (
              <IconTerminal size={18} className="text-secondary" />
            ) : (
              <IconFileCode size={18} className="text-secondary" />
            )}
            <h3 id="drawer-title" className="drawer-title">
              Evidence: <code>{evidence.id}</code>
            </h3>
            <span className={`badge badge-${evidence.kind}`}>
              {evidence.kind}
            </span>
          </div>

          <button
            type="button"
            className="btn-icon"
            onClick={onClose}
            aria-label="Close evidence panel"
          >
            <IconX size={16} />
          </button>
        </header>

        {/* Drawer Content */}
        <div className="drawer-body">
          {/* Metadata Card */}
          <div className="evidence-meta-card">
            {isExecution ? (
              <>
                <div className="meta-row">
                  <span className="meta-label">Evidence Type</span>
                  <span className="meta-value">Controlled Container Execution</span>
                </div>
                <div className="meta-row">
                  <span className="meta-label">Execution ID</span>
                  <code className="meta-code">{evidence.execution_id}</code>
                </div>
                <div className="meta-row">
                  <span className="meta-label">Executed Revision</span>
                  <code className="meta-code">{evidence.revision}</code>
                </div>
                {execution && (
                  <div className="meta-row">
                    <span className="meta-label">Execution Status</span>
                    <span className="meta-value">{execution.status}</span>
                  </div>
                )}
              </>
            ) : (
              <>
                <div className="meta-row">
                  <span className="meta-label">File Path</span>
                  <code className="meta-code">{evidence.path}</code>
                </div>
                <div className="meta-row">
                  <span className="meta-label">Lines</span>
                  <span className="meta-value">
                    L{evidence.start_line} &ndash; L{evidence.end_line}
                  </span>
                </div>
                <div className="meta-row">
                  <span className="meta-label">Pinned Commit</span>
                  <code className="meta-code" title={evidence.revision}>
                    {evidence.revision.slice(0, 12)}
                  </code>
                </div>
              </>
            )}
          </div>

          {/* Action Row */}
          <div className="evidence-actions-row">
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={handleCopyReference}
            >
              {copied ? <IconCheck size={14} /> : <IconCopy size={14} />}
              <span>{copied ? 'Copied reference' : 'Copy reference'}</span>
            </button>

            {permalink && (
              <a
                href={permalink}
                target="_blank"
                rel="noopener noreferrer"
                className="btn btn-secondary btn-sm"
              >
                <IconExternalLink size={14} />
                <span>Open pinned source on GitHub</span>
              </a>
            )}
          </div>

          {/* Code Viewer / Excerpt View */}
          <section className="evidence-code-section">
            <div className="section-label-row">
              <span className="section-title">
                {isExecution ? 'Execution Log Excerpt' : 'Verbatim Source Excerpt'}
              </span>
              <span className="section-note">
                {isExecution
                  ? 'Output from container run'
                  : 'Pinned commit exact lines'}
              </span>
            </div>

            <div className="code-viewer-container">
              <pre className="code-viewer-pre">
                <table className="code-table">
                  <tbody>
                    {excerptLines.map((line, idx) => (
                      <tr key={idx} className="code-line-row">
                        <td className="line-num-cell">
                          {isExecution ? idx + 1 : startLineNum + idx}
                        </td>
                        <td className="line-code-cell">
                          <code>{line || ' '}</code>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </pre>
            </div>
          </section>

          {isExecution && (
            <div className="callout callout-info">
              <strong>Execution Evidence Note:</strong> This excerpt records actual
              pytest runtime output from an isolated container run. It does not
              represent raw source code or prove issue fix completeness.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
