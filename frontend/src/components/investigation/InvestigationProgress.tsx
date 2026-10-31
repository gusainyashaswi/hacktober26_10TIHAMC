import { Stage } from '../../types/analysis';
import {
  IconAlertCircle,
  IconCheck,
  IconClock,
  IconRefresh,
} from '../common/Icons';

interface InvestigationProgressProps {
  stage: Stage;
  analysisId: string;
  errors: string[];
  pollCount: number;
  onStopWaiting: () => void;
  onRefreshNow: () => void;
}

interface StageStep {
  stage: Stage;
  label: string;
  description: string;
}

const STAGE_ORDER: StageStep[] = [
  {
    stage: 'queued',
    label: 'Queued',
    description: 'Analysis request is waiting for a local inference worker.',
  },
  {
    stage: 'loading',
    label: 'Loading pinned source',
    description: 'Downloading and validating repository snapshot for the pinned commit.',
  },
  {
    stage: 'extracting',
    label: 'Extracting technical claims',
    description: 'Prompting local Qwen3-8B to isolate verifiable claims and search terms.',
  },
  {
    stage: 'retrieving',
    label: 'Finding relevant evidence',
    description: 'Locating Python source files, functions, and documentation matching search terms.',
  },
  {
    stage: 'assessing',
    label: 'Reviewing claims',
    description: 'Evaluating claims against retrieved code excerpts (supported, contradicted, inconclusive).',
  },
  {
    stage: 'awaiting_verification',
    label: 'Awaiting test reproduction',
    description: 'Source review complete. Review and approve a focused reproduction test.',
  },
  {
    stage: 'verifying',
    label: 'Running approved test',
    description: 'Executing approved pytest code in a controlled Docker container.',
  },
  {
    stage: 'complete',
    label: 'Investigation complete',
    description: 'All findings, evidence references, and execution records are ready for inspection.',
  },
];

export function InvestigationProgress({
  stage,
  analysisId,
  errors,
  pollCount,
  onStopWaiting,
  onRefreshNow,
}: InvestigationProgressProps) {
  const getStageIndex = (s: Stage) => {
    if (s === 'awaiting_evidence') return 2; // After extracting
    if (s === 'error') return -1;
    return STAGE_ORDER.findIndex((step) => step.stage === s);
  };

  const currentIndex = getStageIndex(stage);
  const isError = stage === 'error';

  return (
    <div className="progress-container" role="region" aria-label="Investigation progress">
      <div className="progress-card">
        <div className="progress-header">
          <div className="progress-title-row">
            <h3 className="progress-title">
              {isError ? 'Investigation Encountered an Error' : 'Investigating Technical Claims'}
            </h3>
            <span className="analysis-id-badge" title="Investigation Identifier">
              ID: <code>{analysisId}</code>
            </span>
          </div>
          <p className="progress-lead">
            Tracking actual backend stages. No fabricated percentages or artificial delays.
          </p>
        </div>

        {/* Step stages visualizer */}
        <div className="stage-steps-list">
          {STAGE_ORDER.map((step, idx) => {
            const isPast = currentIndex > idx;
            const isCurrent = currentIndex === idx;

            let statusClass = 'step-upcoming';
            if (isPast) statusClass = 'step-past';
            if (isCurrent && !isError) statusClass = 'step-current';
            if (isError && isCurrent) statusClass = 'step-error';

            return (
              <div key={step.stage} className={`stage-step-row ${statusClass}`}>
                <div className="step-indicator">
                  {isPast ? (
                    <span className="step-icon step-icon-check">
                      <IconCheck size={12} />
                    </span>
                  ) : isCurrent && !isError ? (
                    <span className="step-icon step-icon-active">
                      <IconRefresh size={12} className="spin" />
                    </span>
                  ) : isCurrent && isError ? (
                    <span className="step-icon step-icon-error">
                      <IconAlertCircle size={12} />
                    </span>
                  ) : (
                    <span className="step-icon step-icon-circle" />
                  )}
                </div>

                <div className="step-content">
                  <div className="step-label-row">
                    <span className="step-label">{step.label}</span>
                    {isCurrent && !isError && (
                      <span className="badge badge-analysing">In Progress</span>
                    )}
                  </div>
                  <span className="step-desc">{step.description}</span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Errors if any */}
        {errors.length > 0 && (
          <div className="callout callout-error" role="alert">
            <IconAlertCircle size={16} className="callout-icon" />
            <div className="callout-content">
              <strong>Backend reports errors:</strong>
              <ul className="error-list">
                {errors.map((err, i) => (
                  <li key={i}>{err}</li>
                ))}
              </ul>
            </div>
          </div>
        )}

        {/* Polling controller bar */}
        {!isError && stage !== 'complete' && (
          <div className="polling-controls">
            <div className="polling-status">
              <IconClock size={14} className="text-muted" />
              <span className="text-muted">
                Polling backend (check #{pollCount}). Analysis typically takes 15–45 seconds.
              </span>
            </div>
            <div className="polling-buttons">
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={onRefreshNow}
              >
                <IconRefresh size={12} />
                <span>Check Now</span>
              </button>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={onStopWaiting}
                title="Stop browser polling. Does not cancel backend processing."
              >
                Stop Waiting
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
