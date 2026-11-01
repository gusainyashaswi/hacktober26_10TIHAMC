import {
  Assessment,
  ComparisonStatus,
  ExecutionStatus,
  Stage,
} from '../../types/analysis';
import { PRAnalysisStatus } from '../../types/repository';
import {
  IconAlertCircle,
  IconAlertTriangle,
  IconCheck,
  IconClock,
  IconRefresh,
} from './Icons';

interface AssessmentBadgeProps {
  assessment: Assessment;
}

export function AssessmentBadge({ assessment }: AssessmentBadgeProps) {
  if (assessment === 'supported') {
    return (
      <span className="badge badge-supported">
        <IconCheck size={12} />
        <span>Supported</span>
      </span>
    );
  }
  if (assessment === 'contradicted') {
    return (
      <span className="badge badge-contradicted">
        <IconAlertCircle size={12} />
        <span>Contradicted</span>
      </span>
    );
  }
  return (
    <span className="badge badge-inconclusive">
      <IconAlertTriangle size={12} />
      <span>Unverified</span>
    </span>
  );
}

interface ExecutionStatusBadgeProps {
  status: ExecutionStatus;
}

export function ExecutionStatusBadge({ status }: ExecutionStatusBadgeProps) {
  switch (status) {
    case 'passed':
      return (
        <span className="badge badge-supported">
          <IconCheck size={12} />
          <span>Passed</span>
        </span>
      );
    case 'failed':
      return (
        <span className="badge badge-contradicted">
          <IconAlertCircle size={12} />
          <span>Failed</span>
        </span>
      );
    case 'setup_error':
      return (
        <span className="badge badge-inconclusive">
          <IconAlertTriangle size={12} />
          <span>Setup Error</span>
        </span>
      );
    case 'timeout':
      return (
        <span className="badge badge-inconclusive">
          <IconClock size={12} />
          <span>Timeout</span>
        </span>
      );
    case 'blocked':
      return (
        <span className="badge badge-neutral">
          <span>Blocked</span>
        </span>
      );
    case 'not_run':
    default:
      return (
        <span className="badge badge-neutral">
          <span>Not Run</span>
        </span>
      );
  }
}

interface ComparisonStatusBadgeProps {
  status: ComparisonStatus;
}

export function ComparisonStatusBadge({ status }: ComparisonStatusBadgeProps) {
  switch (status) {
    case 'fix_verified_for_test':
      return (
        <span className="badge badge-supported">
          <IconCheck size={12} />
          <span>Fix verified for this test</span>
        </span>
      );
    case 'not_reproduced_for_test':
      return (
        <span className="badge badge-inconclusive">
          <IconAlertTriangle size={12} />
          <span>Not reproduced by this test</span>
        </span>
      );
    case 'still_failing':
      return (
        <span className="badge badge-contradicted">
          <IconAlertCircle size={12} />
          <span>Test still fails</span>
        </span>
      );
    case 'inconclusive':
    default:
      return (
        <span className="badge badge-inconclusive">
          <IconAlertTriangle size={12} />
          <span>Unverified</span>
        </span>
      );
  }
}

interface PRStatusBadgeProps {
  status: PRAnalysisStatus;
}

export function PRStatusBadge({ status }: PRStatusBadgeProps) {
  switch (status) {
    case 'not_analysed':
      return <span className="badge badge-neutral">Not analysed</span>;
    case 'queued':
      return (
        <span className="badge badge-queued">
          <IconClock size={12} />
          <span>Queued</span>
        </span>
      );
    case 'analysing':
      return (
        <span className="badge badge-analysing">
          <IconRefresh size={12} className="spin" />
          <span>Analysing</span>
        </span>
      );
    case 'complete':
      return (
        <span className="badge badge-supported">
          <IconCheck size={12} />
          <span>Analysed</span>
        </span>
      );
    case 'failed':
      return (
        <span className="badge badge-contradicted">
          <IconAlertCircle size={12} />
          <span>Failed</span>
        </span>
      );
    case 'outdated':
      return (
        <span className="badge badge-inconclusive">
          <IconAlertTriangle size={12} />
          <span>Outdated (New PR Head)</span>
        </span>
      );
    default:
      return null;
  }
}

interface StageBadgeProps {
  stage: Stage;
}

export function StageBadge({ stage }: StageBadgeProps) {
  const labels: Record<Stage, string> = {
    queued: 'Queued',
    loading: 'Loading source',
    extracting: 'Extracting claims',
    awaiting_evidence: 'Awaiting evidence',
    retrieving: 'Retrieving evidence',
    assessing: 'Reviewing claims',
    awaiting_verification: 'Awaiting test approval',
    verifying: 'Running test',
    complete: 'Investigation complete',
    error: 'Error',
  };

  const isTerminal = stage === 'complete' || stage === 'error';
  const isError = stage === 'error';

  return (
    <span
      className={`badge ${
        isError
          ? 'badge-contradicted'
          : isTerminal
          ? 'badge-supported'
          : 'badge-analysing'
      }`}
    >
      {!isTerminal && <IconRefresh size={12} className="spin" />}
      {isTerminal && !isError && <IconCheck size={12} />}
      {isError && <IconAlertCircle size={12} />}
      <span>{labels[stage] || stage}</span>
    </span>
  );
}

