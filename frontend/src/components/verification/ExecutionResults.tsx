import { useState } from 'react';
import { ApprovedTest, ExecutionResult } from '../../types/analysis';
import { ExecutionStatusBadge } from '../common/StatusBadge';
import {
  IconChevronDown,
  IconChevronRight,
  IconClock,
  IconTerminal,
} from '../common/Icons';

interface ExecutionResultsProps {
  executions: ExecutionResult[];
  approvedTests: ApprovedTest[];
}

export function ExecutionResults({
  executions,
  approvedTests,
}: ExecutionResultsProps) {
  const [expandedLogId, setExpandedLogId] = useState<string | null>(
    executions[0]?.id || null,
  );

  if (executions.length === 0) {
    return null;
  }

  const toggleExpand = (id: string) => {
    setExpandedLogId(expandedLogId === id ? null : id);
  };

  return (
    <div className="executions-container">
      <div className="executions-header">
        <h3 className="section-heading">
          Controlled Container Executions ({executions.length})
        </h3>
        <p className="section-lead">
          Results from isolated container runs. Pytest collection and import errors
          are classified as Setup Errors, not bug reproductions.
        </p>
      </div>

      <div className="executions-list">
        {executions.map((exec) => {
          const isExpanded = expandedLogId === exec.id;
          const matchingApprovedTest = approvedTests.find(
            (t) => t.test_hash === exec.test_hash,
          );

          return (
            <div key={exec.id} className="execution-card">
              {/* Header summary */}
              <div
                className="execution-summary-row"
                onClick={() => toggleExpand(exec.id)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    toggleExpand(exec.id);
                  }
                }}
                aria-expanded={isExpanded}
              >
                <div className="exec-title-group">
                  <span className="expand-chevron">
                    {isExpanded ? (
                      <IconChevronDown size={14} />
                    ) : (
                      <IconChevronRight size={14} />
                    )}
                  </span>
                  <IconTerminal size={15} className="text-secondary" />
                  <span className="exec-id">
                    Run: <code>{exec.id}</code>
                  </span>
                  <span className="exec-revision">
                    commit: <code>{exec.revision.slice(0, 10)}</code>
                  </span>
                </div>

                <div className="exec-status-group">
                  <span className="exec-duration">
                    <IconClock size={12} />
                    <span>{exec.duration_ms} ms</span>
                  </span>
                  <ExecutionStatusBadge status={exec.status} />
                </div>
              </div>

              {/* Collapsible details */}
              {isExpanded && (
                <div className="execution-details-body">
                  <div className="exec-meta-grid">
                    <div className="exec-meta-item">
                      <span className="meta-label">Command:</span>
                      <code className="meta-code-val">
                        {exec.command.join(' ')}
                      </code>
                    </div>
                    <div className="exec-meta-item">
                      <span className="meta-label">Test SHA256:</span>
                      <code className="meta-code-val" title={exec.test_hash}>
                        {exec.test_hash.slice(0, 16)}...
                      </code>
                    </div>
                    {exec.environment.image && (
                      <div className="exec-meta-item">
                        <span className="meta-label">Container Image:</span>
                        <code className="meta-code-val" title={exec.environment.image}>
                          {exec.environment.image}
                        </code>
                      </div>
                    )}
                    {exec.exit_code !== undefined && exec.exit_code !== null && (
                      <div className="exec-meta-item">
                        <span className="meta-label">Exit Code:</span>
                        <span className="meta-val">{exec.exit_code}</span>
                      </div>
                    )}
                  </div>

                  {/* Approved Test Code Source if recorded */}
                  {matchingApprovedTest && (
                    <div className="exec-source-block">
                      <span className="block-title">Approved Test Source:</span>
                      <pre className="code-pre">
                        <code>{matchingApprovedTest.test_code}</code>
                      </pre>
                    </div>
                  )}

                  {/* Stdout Log */}
                  <div className="exec-log-block">
                    <span className="block-title">Container stdout:</span>
                    <pre className="log-pre stdout-pre">
                      <code>{exec.stdout || '(no standard output recorded)'}</code>
                    </pre>
                  </div>

                  {/* Stderr Log */}
                  {exec.stderr && (
                    <div className="exec-log-block">
                      <span className="block-title">Container stderr:</span>
                      <pre className="log-pre stderr-pre">
                        <code>{exec.stderr}</code>
                      </pre>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

