import { useState } from 'react';
import { Claim, VerificationPlan } from '../../types/analysis';
import {
  IconAlertCircle,
  IconPlay,
  IconRefresh,
  IconShield,
} from '../common/Icons';

interface ReproductionFormProps {
  claims: Claim[];
  selectedClaimId?: string;
  hasComparisonRevision: boolean;
  originalRevision: string;
  comparisonRevision?: string | null;
  isRunning: boolean;
  verificationEnabled: boolean;
  onSubmitRun: (plan: VerificationPlan, isComparison: boolean) => Promise<void>;
}

export function ReproductionForm({
  claims,
  selectedClaimId,
  hasComparisonRevision,
  originalRevision,
  comparisonRevision,
  isRunning,
  verificationEnabled,
  onSubmitRun,
}: ReproductionFormProps) {
  const [claimId, setClaimId] = useState(selectedClaimId || claims[0]?.id || '');
  const [testCode, setTestCode] = useState(
    `def test_reproduction():\n    # Enter focused pytest reproduction test code\n    pass\n`,
  );
  const [expectedFailure, setExpectedFailure] = useState('');
  const [isApproved, setIsApproved] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // When claim, testCode or expectedFailure changes, automatically reset approval!
  const handleClaimChange = (newClaimId: string) => {
    setClaimId(newClaimId);
    setIsApproved(false);
    setErrorMessage(null);
  };

  const handleTestCodeChange = (newCode: string) => {
    setTestCode(newCode);
    setIsApproved(false);
    setErrorMessage(null);
  };

  const handleExpectedFailureChange = (val: string) => {
    setExpectedFailure(val);
    setIsApproved(false);
    setErrorMessage(null);
  };

  const handleRun = async (isComparison: boolean) => {
    if (!isApproved) {
      setErrorMessage('Explicit maintainer approval is required before running container tests.');
      return;
    }
    if (!testCode.trim()) {
      setErrorMessage('Test code cannot be empty.');
      return;
    }

    const plan: VerificationPlan = {
      claim_id: claimId,
      test_code: testCode,
      approved: true,
      expected_failure: expectedFailure.trim() ? expectedFailure.trim() : null,
    };

    setErrorMessage(null);
    try {
      await onSubmitRun(plan, isComparison);
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : String(err));
    }
  };

  const canExecute = isApproved && testCode.trim().length > 0 && !isRunning;

  return (
    <div className="reproduction-card" aria-labelledby="reproduction-title">
      <div className="reproduction-header">
        <div className="reproduction-title-row">
          <IconShield size={18} className="text-secondary" />
          <h3 id="reproduction-title" className="reproduction-title">
            Controlled Pytest Reproduction
          </h3>
        </div>
        <p className="reproduction-lead">
          Execute an approved reproduction test inside an isolated, unprivileged Docker container.
        </p>
      </div>

      {!verificationEnabled && (
        <div className="callout callout-warning">
          <IconAlertCircle size={16} className="callout-icon" />
          <div className="callout-content">
            <strong>Controlled verification disabled:</strong> Backend reports that
            container verification is not active (<code className="code-inline">NOBLUFF_ENABLE_VERIFICATION=1</code> required).
            Requests will return status 501.
          </div>
        </div>
      )}

      <div className="form-group">
        <label htmlFor="claim-select" className="form-label">
          Target Claim
        </label>
        <select
          id="claim-select"
          className="form-select"
          value={claimId}
          onChange={(e) => handleClaimChange(e.target.value)}
          disabled={isRunning}
        >
          {claims.map((c) => (
            <option key={c.id} value={c.id}>
              {c.id}: {c.text.length > 80 ? `${c.text.slice(0, 80)}...` : c.text}
            </option>
          ))}
        </select>
      </div>

      <div className="form-group">
        <div className="form-label-row">
          <label htmlFor="test-code-editor" className="form-label">
            Pytest Test Code
          </label>
          <span className="form-label-hint">
            Standard Python 3.11 + pytest only. No network access.
          </span>
        </div>
        <textarea
          id="test-code-editor"
          className="form-textarea test-editor"
          rows={7}
          value={testCode}
          onChange={(e) => handleTestCodeChange(e.target.value)}
          disabled={isRunning}
          spellCheck={false}
          aria-describedby="test-code-hint"
        />
        <span id="test-code-hint" className="sr-only">
          Modifying test code resets approval.
        </span>
      </div>

      <div className="form-group">
        <label htmlFor="expected-failure-input" className="form-label">
          Expected Exception Class (Optional)
        </label>
        <input
          id="expected-failure-input"
          type="text"
          className="form-input"
          placeholder="e.g. ValueError, KeyError, ZeroDivisionError"
          value={expectedFailure}
          onChange={(e) => handleExpectedFailureChange(e.target.value)}
          disabled={isRunning}
        />
        <span className="input-hint">
          If provided, the runner checks that the test fails with this exact Python exception.
        </span>
      </div>

      {/* Controlled Environment Guarantees */}
      <div className="environment-guarantees-card">
        <div className="guarantees-header">
          <IconShield size={14} />
          <span>Container Safety Controls</span>
        </div>
        <ul className="guarantees-list">
          <li><strong>Network:</strong> Disabled entirely (<code className="code-inline">--network none</code>).</li>
          <li><strong>Filesystem:</strong> Source mounted read-only; unprivileged non-root user.</li>
          <li><strong>Resource limits:</strong> 1 CPU, 256 MB RAM, max 64 PIDs, 15-second deadline.</li>
          <li><strong>Execution boundary:</strong> Fixed command (<code className="code-inline">pytest -q _nobluff_reproduction/test_approved.py</code>).</li>
        </ul>
      </div>

      {/* Explicit Approval Checkbox */}
      <div className="approval-checkbox-row">
        <label className="checkbox-label" htmlFor="explicit-approval-check">
          <input
            id="explicit-approval-check"
            type="checkbox"
            className="form-checkbox"
            checked={isApproved}
            onChange={(e) => {
              setIsApproved(e.target.checked);
              setErrorMessage(null);
            }}
            disabled={isRunning}
          />
          <span className="checkbox-text">
            I have reviewed this pytest code and explicitly approve executing it in the controlled container.
          </span>
        </label>
      </div>

      {errorMessage && (
        <div className="callout callout-error" role="alert">
          <IconAlertCircle size={16} className="callout-icon" />
          <div className="callout-content">{errorMessage}</div>
        </div>
      )}

      {/* Execution Buttons */}
      <div className="reproduction-actions">
        <button
          type="button"
          className="btn btn-primary"
          onClick={() => handleRun(false)}
          disabled={!canExecute}
        >
          {isRunning ? (
            <IconRefresh size={14} className="spin" />
          ) : (
            <IconPlay size={14} />
          )}
          <span>Run on original ({originalRevision.slice(0, 7)})</span>
        </button>

        {hasComparisonRevision && comparisonRevision && (
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => handleRun(true)}
            disabled={!canExecute}
            title="Runs identical test bytes against original and proposed fix revisions"
          >
            {isRunning ? (
              <IconRefresh size={14} className="spin" />
            ) : (
              <IconPlay size={14} />
            )}
            <span>
              Compare original ({originalRevision.slice(0, 7)}) &amp; fix ({comparisonRevision.slice(0, 7)})
            </span>
          </button>
        )}
      </div>
    </div>
  );
}
