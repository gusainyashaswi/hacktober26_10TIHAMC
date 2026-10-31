import {
  ComparisonResult,
  ExecutionResult,
} from '../../types/analysis';
import {
  ComparisonStatusBadge,
  ExecutionStatusBadge,
} from '../common/StatusBadge';
import {
  IconCheck,
  IconClock,
  IconShield,
  IconTerminal,
} from '../common/Icons';

interface ComparisonViewProps {
  comparisons: ComparisonResult[];
  executions: ExecutionResult[];
  originalRevision: string;
  comparisonRevision?: string | null;
}

export function ComparisonView({
  comparisons,
  executions,
  originalRevision,
  comparisonRevision,
}: ComparisonViewProps) {
  if (comparisons.length === 0) return null;

  const execMap = new Map<string, ExecutionResult>();
  executions.forEach((e) => execMap.set(e.id, e));

  return (
    <div className="comparison-section" role="region" aria-label="Before and after comparison">
      <div className="comparison-header">
        <div className="comparison-title-row">
          <IconShield size={18} className="text-secondary" />
          <h3 className="section-heading">Same-Test Before &amp; After Comparison</h3>
        </div>
        <p className="section-lead">
          Identical approved test bytes executed against the original revision and the proposed fix snapshot.
        </p>
      </div>

      <div className="comparisons-list">
        {comparisons.map((comp, idx) => {
          const originalExec = execMap.get(comp.original_execution_id);
          const fixExec = execMap.get(comp.comparison_execution_id);

          return (
            <div key={idx} className="comparison-card">
              {/* Verdict header banner */}
              <div className="comparison-verdict-banner">
                <div className="verdict-status-row">
                  <ComparisonStatusBadge status={comp.status} />
                  <span className="hash-verified-chip">
                    <IconCheck size={12} />
                    <span>Identical Test Bytes Verified ({comp.test_hash.slice(0, 10)})</span>
                  </span>
                </div>

                <div className="verdict-explanation">
                  {comp.status === 'fix_verified_for_test' && (
                    <p className="verdict-text">
                      The approved test reproduced the declared exception on the original revision and passed cleanly on the proposed fix.
                    </p>
                  )}
                  {comp.status === 'not_reproduced_for_test' && (
                    <p className="verdict-text">
                      The approved test passed on the original revision. This does not disprove the reported issue.
                    </p>
                  )}
                  {comp.status === 'still_failing' && (
                    <p className="verdict-text">
                      The test failed on the original revision and still failed after the proposed changes. Inspect both output logs below.
                    </p>
                  )}
                  {comp.status === 'inconclusive' && (
                    <p className="verdict-text">
                      The comparison was inconclusive due to container setup errors, timeout, or environment differences.
                    </p>
                  )}
                </div>

                {/* Important Scope Disclaimer */}
                <div className="comparison-scope-notice">
                  <strong>Scope limitation:</strong> This result applies strictly to
                  this test, these snapshot revisions, and the recorded container
                  environment. It does not prove the pull request is complete or free
                  of edge-case bugs.
                </div>
              </div>

              {/* Side-by-side execution display */}
              <div className="comparison-columns-grid">
                {/* Original Column */}
                <div className="comparison-col comparison-col-before">
                  <div className="col-header">
                    <span className="col-tag">Original Revision</span>
                    <code className="commit-hash" title={originalRevision}>
                      {originalRevision.slice(0, 12)}
                    </code>
                    {originalExec && (
                      <ExecutionStatusBadge status={originalExec.status} />
                    )}
                  </div>

                  {originalExec ? (
                    <div className="col-content">
                      <div className="run-metrics">
                        <span>Run: <code>{originalExec.id}</code></span>
                        <span>
                          <IconClock size={11} /> {originalExec.duration_ms} ms
                        </span>
                      </div>
                      <div className="log-window">
                        <div className="log-window-header">
                          <IconTerminal size={12} />
                          <span>stdout / stderr</span>
                        </div>
                        <pre className="log-pre">
                          <code>{originalExec.stdout || originalExec.stderr || '(empty log)'}</code>
                        </pre>
                      </div>
                    </div>
                  ) : (
                    <div className="empty-col">No execution recorded for original revision.</div>
                  )}
                </div>

                {/* Proposed Fix Column */}
                <div className="comparison-col comparison-col-after">
                  <div className="col-header">
                    <span className="col-tag">Proposed Fix</span>
                    <code
                      className="commit-hash"
                      title={comparisonRevision || fixExec?.revision || 'unknown'}
                    >
                      {(comparisonRevision || fixExec?.revision || 'unknown').slice(0, 12)}
                    </code>
                    {fixExec && (
                      <ExecutionStatusBadge status={fixExec.status} />
                    )}
                  </div>

                  {fixExec ? (
                    <div className="col-content">
                      <div className="run-metrics">
                        <span>Run: <code>{fixExec.id}</code></span>
                        <span>
                          <IconClock size={11} /> {fixExec.duration_ms} ms
                        </span>
                      </div>
                      <div className="log-window">
                        <div className="log-window-header">
                          <IconTerminal size={12} />
                          <span>stdout / stderr</span>
                        </div>
                        <pre className="log-pre">
                          <code>{fixExec.stdout || fixExec.stderr || '(empty log)'}</code>
                        </pre>
                      </div>
                    </div>
                  ) : (
                    <div className="empty-col">No execution recorded for proposed fix revision.</div>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
