import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import App from './App';
import * as client from './api/client';
import { saveConnectedRepositories, saveSelectedRepoId } from './api/storage';
import { AnalysisReport } from './types/analysis';

describe('NoBluff Connect-Once and PR Workflow', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();

    // Default health mock
    vi.spyOn(client, 'fetchHealth').mockResolvedValue({
      status: 'ok',
      scope: 'source_review',
      model: 'qwen3:8b',
      model_readiness: 'ready',
      repository_loading: true,
      evidence_assessment: true,
      verification: true,
    });
  });

  afterEach(() => {
    vi.clearAllTimers();
  });

  it('renders connect screen on initial visit with no connected repo and connects repository (Requirement 1)', async () => {
    render(<App />);

    // Connect modal should appear automatically on first visit
    expect(screen.getByRole('heading', { name: /connect repository/i })).toBeInTheDocument();
    expect(
      screen.getByText(/NoBluff extracts technical claims from pull requests/i),
    ).toBeInTheDocument();

    const input = screen.getByLabelText(/github repository/i);
    fireEvent.change(input, { target: { value: 'pallets/flask' } });

    const connectBtn = screen.getByRole('button', { name: /connect repository/i });
    fireEvent.click(connectBtn);

    // Wait for connection and inbox to appear
    await waitFor(() => {
      expect(screen.queryByRole('heading', { name: /connect repository/i })).not.toBeInTheDocument();
      expect(screen.getByText('flask')).toBeInTheDocument();
    });
  });

  it('restores connected repository and loads PR inbox automatically across sessions (Requirement 1 & 2)', async () => {
    saveConnectedRepositories([
      {
        id: 'pallets/flask',
        owner: 'pallets',
        name: 'flask',
        fullName: 'pallets/flask',
        url: 'https://github.com/pallets/flask',
        defaultBranch: 'main',
        isPrivate: false,
        connectedAt: new Date().toISOString(),
      },
    ]);
    saveSelectedRepoId('pallets/flask');

    render(<App />);

    // Should directly render PR Inbox without showing Connect modal
    expect(screen.queryByRole('heading', { name: /connect repository/i })).not.toBeInTheDocument();
    expect(screen.getByText('flask')).toBeInTheDocument();

    // PR rows should load automatically
    await waitFor(() => {
      expect(screen.getByText(/#4892/i)).toBeInTheDocument();
      expect(
        screen.getByText(/Fix request argument parsing when query string contains malformed/i),
      ).toBeInTheDocument();
    });

    // Clearly labeled development adapter banner (Requirement 14)
    expect(screen.getByText(/Dev Adapter/i)).toBeInTheDocument();
  });

  it('selects a PR without manually pasting its description and displays comparison revisions (Requirement 3)', async () => {
    saveConnectedRepositories([
      {
        id: 'pallets/flask',
        owner: 'pallets',
        name: 'flask',
        fullName: 'pallets/flask',
        url: 'https://github.com/pallets/flask',
        defaultBranch: 'main',
        isPrivate: false,
        connectedAt: new Date().toISOString(),
      },
    ]);
    saveSelectedRepoId('pallets/flask');

    render(<App />);

    // Wait for PR list to render
    const prRow = await screen.findByText(/#4892/i);
    fireEvent.click(prRow);

    // Inspect PR Details workspace
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /Fix request argument parsing/i })).toBeInTheDocument();
      expect(screen.getByText(/Base Comparison Revision/i)).toBeInTheDocument();
      expect(screen.getByText(/PR Head Revision/i)).toBeInTheDocument();
      expect(screen.getByText('d5c21f0a82e75e5eb461b203498a964e52b2ef81')).toBeInTheDocument();
      expect(screen.getByText('f849a64e1c28c89b2751f7253507d62058fa72da')).toBeInTheDocument();
    });
  });

  it('submits analysis with backend-provided context and stops polling at terminal complete state (Requirement 4 & 5)', async () => {
    saveConnectedRepositories([
      {
        id: 'pallets/flask',
        owner: 'pallets',
        name: 'flask',
        fullName: 'pallets/flask',
        url: 'https://github.com/pallets/flask',
        defaultBranch: 'main',
        isPrivate: false,
        connectedAt: new Date().toISOString(),
      },
    ]);
    saveSelectedRepoId('pallets/flask');

    const submitSpy = vi.spyOn(client, 'submitAnalysis').mockResolvedValue({
      id: 'analysis-1234',
    });

    const mockReport: AnalysisReport = {
      schema_version: '1.0',
      id: 'analysis-1234',
      repository: 'https://github.com/pallets/flask',
      revision: 'd5c21f0a82e75e5eb461b203498a964e52b2ef81',
      comparison_revision: 'f849a64e1c28c89b2751f7253507d62058fa72da',
      model: 'qwen3:8b',
      stage: 'complete',
      claims: [
        {
          id: 'claim-1',
          text: 'unquote raises UnicodeDecodeError',
          kind: 'behavior',
          search_terms: ['unquote'],
          reported_as: 'assertion',
        },
      ],
      evidence: [],
      findings: [
        {
          claim_id: 'claim-1',
          assessment: 'inconclusive',
          evidence_ids: [],
          explanation: 'Requires runtime evaluation.',
          limitations: ['Static inspection only.'],
        },
      ],
      executions: [],
      approved_tests: [],
      comparisons: [],
      errors: [],
    };

    const fetchSpy = vi.spyOn(client, 'fetchAnalysis').mockResolvedValue(mockReport);

    render(<App />);

    // Select PR
    const prRow = await screen.findByText(/#4892/i);
    fireEvent.click(prRow);

    // Click Analyse PR
    const analyseBtn = await screen.findByRole('button', { name: /analyse pr/i });
    fireEvent.click(analyseBtn);

    // Verify submitAnalysis called with backend context
    await waitFor(() => {
      expect(submitSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          repository: 'https://github.com/pallets/flask',
          revision: 'd5c21f0a82e75e5eb461b203498a964e52b2ef81',
          comparison_revision: 'f849a64e1c28c89b2751f7253507d62058fa72da',
        }),
      );
    });

    // Verification of findings loaded
    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledWith('analysis-1234');
      expect(
        screen.getByRole('heading', { name: /unquote raises UnicodeDecodeError/i }),
      ).toBeInTheDocument();
      expect(screen.getByText('Inconclusive')).toBeInTheDocument();
    });
  });

  it('marks an analysis stale when PR head commit changes (Requirement 13)', async () => {
    saveConnectedRepositories([
      {
        id: 'pallets/flask',
        owner: 'pallets',
        name: 'flask',
        fullName: 'pallets/flask',
        url: 'https://github.com/pallets/flask',
        defaultBranch: 'main',
        isPrivate: false,
        connectedAt: new Date().toISOString(),
      },
    ]);
    saveSelectedRepoId('pallets/flask');

    // Simulate an older analysis against an earlier commit
    localStorage.setItem(
      'nobluff:pr_analysis_map:pallets/flask',
      JSON.stringify({
        4892: {
          analysisId: 'old-analysis-001',
          analysedHeadCommit: 'earlier-commit-hash-00000',
          status: 'complete',
          updatedAt: new Date().toISOString(),
        },
      }),
    );

    render(<App />);

    // Wait for inbox to display outdated badge
    await waitFor(() => {
      expect(screen.getByText(/Outdated \(New PR Head\)/i)).toBeInTheDocument();
    });

    // Click into details
    const investigateBtns = screen.getAllByRole('button', { name: /investigate/i });
    fireEvent.click(investigateBtns[0]);

    // PR Details should show the stale warning banner
    await waitFor(() => {
      expect(screen.getByText(/PR head commit changed:/i)).toBeInTheDocument();
      expect(
        screen.getAllByRole('button', { name: /analyse latest revision/i }).length,
      ).toBeGreaterThanOrEqual(1);
    });
  });

  it('preserves user context and shows useful error on network failure (Requirement 8)', async () => {
    saveConnectedRepositories([
      {
        id: 'pallets/flask',
        owner: 'pallets',
        name: 'flask',
        fullName: 'pallets/flask',
        url: 'https://github.com/pallets/flask',
        defaultBranch: 'main',
        isPrivate: false,
        connectedAt: new Date().toISOString(),
      },
    ]);
    saveSelectedRepoId('pallets/flask');

    // Mock network failure for submitAnalysis
    vi.spyOn(client, 'submitAnalysis').mockRejectedValue(
      new Error('Backend connection refused (port 8000)'),
    );
    const alertMock = vi.spyOn(window, 'alert').mockImplementation(() => {});

    render(<App />);

    const prRow = await screen.findByText(/#4892/i);
    fireEvent.click(prRow);

    const analyseBtn = await screen.findByRole('button', { name: /analyse pr/i });
    fireEvent.click(analyseBtn);

    await waitFor(() => {
      expect(alertMock).toHaveBeenCalledWith('Backend connection refused (port 8000)');
      // Context is preserved: user is still on the PR detail screen
      expect(screen.getByRole('heading', { name: /Fix request argument parsing/i })).toBeInTheDocument();
    });
  });
});
