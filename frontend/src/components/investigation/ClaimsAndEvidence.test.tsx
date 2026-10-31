import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { ClaimsList } from './ClaimsList';
import { EvidenceDrawer } from '../evidence/EvidenceDrawer';
import { Claim, Evidence, Finding } from '../../types/analysis';

describe('Screens 5 & 6: Claims, Findings and Evidence Drawer', () => {
  const dummyClaims: Claim[] = [
    {
      id: 'claim-1',
      text: 'urllib unquote raises UnicodeDecodeError on invalid percent encodings',
      kind: 'behavior',
      search_terms: ['unquote', 'UnicodeDecodeError'],
      reported_as: 'assertion',
    },
    {
      id: 'claim-2',
      text: 'Flask query parser handles empty parameters without crashing',
      kind: 'behavior',
      search_terms: ['parse_qs'],
      reported_as: 'hypothesis',
    },
  ];

  const dummyEvidence: Evidence[] = [
    {
      id: 'ev-1',
      kind: 'source',
      revision: 'd5c21f0a82e75e5eb461b203498a964e52b2ef81',
      path: 'src/flask/wrappers.py',
      start_line: 42,
      end_line: 48,
      excerpt: 'def _load_form_data(self):\n    return self.parameter_storage_class()',
    },
  ];

  const dummyFindings: Finding[] = [
    {
      claim_id: 'claim-1',
      assessment: 'supported',
      evidence_ids: ['ev-1'],
      explanation: 'Verified in src/flask/wrappers.py:42 that unquote is invoked directly without error wrapping.',
      limitations: ['Static source inspection cannot establish WSGI server error handling.'],
      suggested_next_step: 'Run reproduction test under WSGI harness.',
    },
    {
      claim_id: 'claim-2',
      assessment: 'inconclusive',
      evidence_ids: [],
      explanation: 'No direct source code evidence retrieved confirming empty parameter handling.',
      limitations: ['Repository retrieval found no matching definitions for empty parameter handling.'],
      suggested_next_step: 'Inspect werkzeug request parameter parser.',
    },
  ];

  it('renders findings and triggers opening evidence on chip click (Requirement 6)', () => {
    const onSelectEvidence = vi.fn();
    render(
      <ClaimsList
        claims={dummyClaims}
        findings={dummyFindings}
        evidence={dummyEvidence}
        onSelectEvidence={onSelectEvidence}
      />,
    );

    // Finding 1 is supported
    expect(screen.getByText('Supported')).toBeInTheDocument();
    expect(screen.getByText(/Verified in src\/flask\/wrappers\.py/i)).toBeInTheDocument();

    // Chip for ev-1
    const chip = screen.getByRole('button', { name: /src\/flask\/wrappers\.py:42/i });
    expect(chip).toBeInTheDocument();
    fireEvent.click(chip);
    expect(onSelectEvidence).toHaveBeenCalledWith('ev-1');
  });

  it('displays missing-evidence and inconclusive states honestly (Requirement 7)', () => {
    render(
      <ClaimsList
        claims={dummyClaims}
        findings={dummyFindings}
        evidence={dummyEvidence}
        onSelectEvidence={vi.fn()}
      />,
    );

    // Finding 2 is inconclusive
    expect(screen.getByText('Inconclusive')).toBeInTheDocument();
    expect(
      screen.getByText(/Missing Evidence \/ Inconclusive Factor:/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Repository retrieval found no matching definitions/i),
    ).toBeInTheDocument();
  });

  it('displays honest empty state when no technical claims were extracted', () => {
    render(
      <ClaimsList
        claims={[]}
        findings={[]}
        evidence={[]}
        onSelectEvidence={vi.fn()}
      />,
    );

    expect(
      screen.getByText(/No technical claims extracted/i),
    ).toBeInTheDocument();
  });

  it('renders the evidence drawer with exact line numbers and closes on Escape', () => {
    const onClose = vi.fn();
    render(
      <EvidenceDrawer
        isOpen={true}
        evidence={dummyEvidence[0]}
        repositoryUrl="https://github.com/pallets/flask"
        onClose={onClose}
      />,
    );

    expect(screen.getByText(/src\/flask\/wrappers\.py/i)).toBeInTheDocument();
    expect(screen.getByText(/L42 – L48/i)).toBeInTheDocument();
    expect(screen.getByText('42')).toBeInTheDocument();
    expect(screen.getByText('43')).toBeInTheDocument();
    expect(screen.getByText(/def _load_form_data/i)).toBeInTheDocument();

    // Test GitHub permalink
    const permalink = screen.getByRole('link', { name: /open pinned source on github/i });
    expect(permalink).toHaveAttribute(
      'href',
      'https://github.com/pallets/flask/blob/d5c21f0a82e75e5eb461b203498a964e52b2ef81/src/flask/wrappers.py#L42-L48',
    );

    // Press Escape
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(onClose).toHaveBeenCalled();
  });
});
