import {
  Claim,
  Evidence,
  Finding,
} from '../../types/analysis';
import { AssessmentBadge } from '../common/StatusBadge';
import {
  IconAlertTriangle,
  IconArrowRight,
  IconFileCode,
  IconInfo,
} from '../common/Icons';

interface ClaimsListProps {
  claims: Claim[];
  findings: Finding[];
  evidence: Evidence[];
  onSelectEvidence: (evidenceId: string) => void;
  onStartVerificationForClaim?: (claimId: string) => void;
}

export function ClaimsList({
  claims,
  findings,
  evidence,
  onSelectEvidence,
  onStartVerificationForClaim,
}: ClaimsListProps) {
  // Map claim ID to finding
  const findingsMap = new Map<string, Finding>();
  findings.forEach((f) => findingsMap.set(f.claim_id, f));

  // Map evidence ID to evidence object
  const evidenceMap = new Map<string, Evidence>();
  evidence.forEach((e) => evidenceMap.set(e.id, e));

  if (claims.length === 0) {
    return (
      <div className="empty-state card">
        <IconInfo size={28} className="text-muted" />
        <h4 className="empty-title">No technical claims extracted</h4>
        <p className="empty-desc">
          No verifiable technical claims were isolated from the report text. The issue
          or PR description may describe a feature request or lack technical assertions.
        </p>
      </div>
    );
  }

  return (
    <div className="claims-list-container">
      <div className="claims-list-header">
        <h3 className="section-heading">
          Technical Claims and Findings ({claims.length})
        </h3>
        <p className="section-lead">
          Claims extracted by local Qwen3-8B and evaluated against pinned repository source.
        </p>
      </div>

      <div className="claims-cards-grid">
        {claims.map((claim) => {
          const finding = findingsMap.get(claim.id);

          return (
            <article key={claim.id} className="claim-card" aria-labelledby={`claim-${claim.id}-title`}>
              {/* Claim Top Bar */}
              <div className="claim-top-row">
                <div className="claim-meta-tags">
                  <span className="claim-id-tag">
                    <code>{claim.id}</code>
                  </span>
                  <span className={`badge badge-subtle badge-${claim.reported_as}`}>
                    {claim.reported_as === 'assertion' ? 'Reported Assertion' : 'Hypothesis'}
                  </span>
                  <span className="badge badge-subtle">
                    {claim.kind}
                  </span>
                </div>

                <div className="claim-verdict-wrap">
                  {finding ? (
                    <AssessmentBadge assessment={finding.assessment} />
                  ) : (
                    <span className="badge badge-neutral">Unassessed</span>
                  )}
                </div>
              </div>

              {/* Claim Text */}
              <div className="claim-body">
                <h4 id={`claim-${claim.id}-title`} className="claim-text">
                  &ldquo;{claim.text}&rdquo;
                </h4>

                {/* Finding Explanation */}
                {finding && (
                  <div className="finding-explanation-block">
                    <p className="finding-explanation">
                      {finding.explanation}
                    </p>

                    {/* Linked Evidence Chips */}
                    {finding.evidence_ids.length > 0 && (
                      <div className="linked-evidence-row">
                        <span className="evidence-row-label">Source Evidence:</span>
                        <div className="evidence-chips-list">
                          {finding.evidence_ids.map((evId) => {
                            const ev = evidenceMap.get(evId);
                            const label = ev?.path
                              ? `${ev.path}:${ev.start_line || 1}`
                              : evId;

                            return (
                              <button
                                key={evId}
                                type="button"
                                className="evidence-chip"
                                onClick={() => onSelectEvidence(evId)}
                                title="Click to view line excerpt and pinned commit"
                              >
                                <IconFileCode size={12} />
                                <span>{label}</span>
                              </button>
                            );
                          })}
                        </div>
                      </div>
                    )}

                    {/* Inconclusive / Limitations Callout */}
                    {finding.limitations.length > 0 && (
                      <div className="finding-limitations-box">
                        <div className="limitations-header">
                          <IconAlertTriangle size={13} className="text-amber" />
                          <span className="limitations-title">
                            {finding.assessment === 'inconclusive'
                              ? 'Missing Evidence / Unverified Factor:'
                              : 'Limitations & Scope:'}
                          </span>
                        </div>
                        <ul className="limitations-list">
                          {finding.limitations.map((lim, i) => (
                            <li key={i}>{lim}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Suggested Next Step */}
                    {finding.suggested_next_step && (
                      <div className="suggested-step-row">
                        <IconArrowRight size={13} className="text-muted" />
                        <span className="suggested-step-text">
                          <strong>Next step:</strong> {finding.suggested_next_step}
                        </span>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Action footer */}
              {onStartVerificationForClaim && (
                <div className="claim-card-footer">
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={() => onStartVerificationForClaim(claim.id)}
                  >
                    <span>Approve reproduction test for {claim.id}</span>
                  </button>
                </div>
              )}
            </article>
          );
        })}
      </div>
    </div>
  );
}
