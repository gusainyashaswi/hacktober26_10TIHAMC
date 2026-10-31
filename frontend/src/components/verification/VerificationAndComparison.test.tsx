import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { ReproductionForm } from './ReproductionForm';
import { ExecutionResults } from './ExecutionResults';
import { ComparisonView } from './ComparisonView';
import {
  Claim,
  ComparisonResult,
  ExecutionResult,
} from '../../types/analysis';

describe('Screen 7: Approved Reproduction Form', () => {
  const dummyClaims: Claim[] = [
    {
      id: 'claim-1',
      text: 'Query parser crashes on malformed percent encodings',
      kind: 'behavior',
      search_terms: ['unquote', 'query'],
      reported_as: 'assertion',
    },
  ];

  it('requires explicit maintainer approval before allowing execution (Requirement 9)', () => {
    const onSubmitRun = vi.fn().mockResolvedValue(undefined);
    render(
      <ReproductionForm
        claims={dummyClaims}
        selectedClaimId="claim-1"
        hasComparisonRevision={true}
        originalRevision="d5c21f0a82e75e5eb461b203498a964e52b2ef81"
        comparisonRevision="f849a64e1c28c89b2751f7253507d62058fa72da"
        isRunning={false}
        verificationEnabled={true}
        onSubmitRun={onSubmitRun}
      />,
    );

    // Run buttons should be disabled initially because checkbox is unchecked
    const runOriginalBtn = screen.getByRole('button', { name: /run on original/i });
    expect(runOriginalBtn).toBeDisabled();

    // Check approval
    const approvalCheck = screen.getByRole('checkbox', {
      name: /explicitly approve executing it/i,
    });
    expect(approvalCheck).not.toBeChecked();

    fireEvent.click(approvalCheck);
    expect(approvalCheck).toBeChecked();
    expect(runOriginalBtn).toBeEnabled();

    // Trigger run
    fireEvent.click(runOriginalBtn);
    expect(onSubmitRun).toHaveBeenCalledWith(
      expect.objectContaining({
        claim_id: 'claim-1',
        approved: true,
      }),
      false,
    );
  });

  it('resets approval whenever test code or expected failure is modified (Requirement 10)', () => {
    const onSubmitRun = vi.fn().mockResolvedValue(undefined);
    render(
      <ReproductionForm
        claims={dummyClaims}
        selectedClaimId="claim-1"
        hasComparisonRevision={false}
        originalRevision="d5c21f0a82e75e5eb461b203498a964e52b2ef81"
        isRunning={false}
        verificationEnabled={true}
        onSubmitRun={onSubmitRun}
      />,
    );

    const approvalCheck = screen.getByRole('checkbox', {
      name: /explicitly approve executing it/i,
    });
    const runBtn = screen.getByRole('button', { name: /run on original/i });

    // Approve
    fireEvent.click(approvalCheck);
    expect(approvalCheck).toBeChecked();
    expect(runBtn).toBeEnabled();

    // Edit test code
    const editor = screen.getByLabelText(/pytest test code/i);
    fireEvent.change(editor, { target: { value: 'def test_new(): pass' } });

    // Approval must be automatically reset
    expect(approvalCheck).not.toBeChecked();
    expect(runBtn).toBeDisabled();

    // Re-approve and edit expected failure
    fireEvent.click(approvalCheck);
    expect(approvalCheck).toBeChecked();
    expect(runBtn).toBeEnabled();

    const expInput = screen.getByLabelText(/expected exception class/i);
    fireEvent.change(expInput, { target: { value: 'ValueError' } });

    // Approval must be reset again
    expect(approvalCheck).not.toBeChecked();
    expect(runBtn).toBeDisabled();
  });
});

describe('Screen 8: Execution Results', () => {
  it('renders setup errors and timeouts correctly without claiming bug reproduction (Requirement 11)', () => {
    const executions: ExecutionResult[] = [
      {
        id: 'exec-setup-err',
        revision: 'd5c21f0a82e75e5eb461b203498a964e52b2ef81',
        test_hash: 'a'.repeat(64),
        command: ['pytest', '-q', '_nobluff_reproduction/test_approved.py'],
        environment: { image: 'sha256:1234567890abcdef' },
        status: 'setup_error',
        exit_code: 4,
        stdout: 'ModuleNotFoundError: No module named pytest_mock',
        stderr: '',
        duration_ms: 120,
      },
      {
        id: 'exec-timeout',
        revision: 'd5c21f0a82e75e5eb461b203498a964e52b2ef81',
        test_hash: 'b'.repeat(64),
        command: ['pytest', '-q', '_nobluff_reproduction/test_approved.py'],
        environment: { image: 'sha256:1234567890abcdef' },
        status: 'timeout',
        exit_code: null,
        stdout: '',
        stderr: 'Execution deadline exceeded: 15 seconds',
        duration_ms: 15000,
      },
    ];

    render(<ExecutionResults executions={executions} approvedTests={[]} />);

    expect(screen.getByText('Setup Error')).toBeInTheDocument();
    expect(screen.getByText('Timeout')).toBeInTheDocument();
    expect(screen.getByText(/ModuleNotFoundError/i)).toBeInTheDocument();
    expect(
      screen.getByText(/Pytest collection and import errors are classified as Setup Errors/i),
    ).toBeInTheDocument();
  });
});

describe('Screen 9: Before/After Comparison View', () => {
  it('renders a scoped before/after result with identical test bytes verification (Requirement 12)', () => {
    const comparisons: ComparisonResult[] = [
      {
        claim_id: 'claim-1',
        original_execution_id: 'run-orig',
        comparison_execution_id: 'run-fix',
        test_hash: 'c'.repeat(64),
        status: 'fix_verified_for_test',
        limitations: [
          'Verdict applies only to the approved test, selected snapshots, and recorded environment.',
        ],
      },
    ];

    const executions: ExecutionResult[] = [
      {
        id: 'run-orig',
        revision: '1111111111111111111111111111111111111111',
        test_hash: 'c'.repeat(64),
        command: ['pytest', 'test.py'],
        environment: { image: 'sha256:abcdef' },
        status: 'failed',
        exit_code: 1,
        stdout: 'E   ValueError: Invalid percent encoding',
        stderr: '',
        duration_ms: 350,
      },
      {
        id: 'run-fix',
        revision: '2222222222222222222222222222222222222222',
        test_hash: 'c'.repeat(64),
        command: ['pytest', 'test.py'],
        environment: { image: 'sha256:abcdef' },
        status: 'passed',
        exit_code: 0,
        stdout: '1 passed in 0.12s',
        stderr: '',
        duration_ms: 220,
      },
    ];

    render(
      <ComparisonView
        comparisons={comparisons}
        executions={executions}
        originalRevision="1111111111111111111111111111111111111111"
        comparisonRevision="2222222222222222222222222222222222222222"
      />,
    );

    expect(screen.getByText(/Fix verified for this test/i)).toBeInTheDocument();
    expect(screen.getByText(/Identical Test Bytes Verified/i)).toBeInTheDocument();
    expect(
      screen.getByText(/This result applies strictly to this test, these snapshot revisions/i),
    ).toBeInTheDocument();
    expect(screen.getByText('Original Revision')).toBeInTheDocument();
    expect(screen.getByText('Proposed Fix')).toBeInTheDocument();
  });
});
