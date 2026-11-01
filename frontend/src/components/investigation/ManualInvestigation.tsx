import React, { useState } from 'react';
import { ConnectedRepository } from '../../types/repository';
import { AnalysisRequest } from '../../types/analysis';
import {
  IconAlertCircle,
  IconPlay,
  IconRefresh,
  IconTerminal,
} from '../common/Icons';

interface ManualInvestigationProps {
  currentRepository?: ConnectedRepository | null;
  isSubmitting: boolean;
  onSubmit: (request: AnalysisRequest) => Promise<void>;
}

export function ManualInvestigation({
  currentRepository,
  isSubmitting,
  onSubmit,
}: ManualInvestigationProps) {
  const [repository, setRepository] = useState(
    currentRepository?.full_name || 'https://github.com/pallets/flask',
  );
  const [revision, setRevision] = useState('main');
  const [comparisonRevision, setComparisonRevision] = useState('');
  const [reportText, setReportText] = useState('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!repository.trim()) {
      setErrorMessage('Repository is required.');
      return;
    }
    if (!revision.trim()) {
      setErrorMessage('Original revision is required.');
      return;
    }
    if (!reportText.trim()) {
      setErrorMessage('Report or issue text is required.');
      return;
    }

    setErrorMessage(null);
    try {
      await onSubmit({
        repository: repository.trim(),
        revision: revision.trim(),
        report_text: reportText.trim(),
        comparison_revision: comparisonRevision.trim() || null,
      });
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : String(err));
    }
  };

  const handleLoadDemoCase = (type: 'csv' | 'flask') => {
    if (type === 'csv') {
      setRepository('https://github.com/pallets/flask');
      setRevision('main');
      setComparisonRevision('');
      setReportText(
        'The query parameter parser crashes when unicode characters or invalid percent encodings appear in the request URL. It raises UnicodeDecodeError in unquote instead of treating it as bad request.',
      );
    } else {
      setRepository('https://github.com/psf/requests');
      setRevision('main');
      setComparisonRevision('');
      setReportText(
        'When both Content-Length and Transfer-Encoding chunked headers are present, Requests sends both over the wire, causing proxy desync per RFC 7230.',
      );
    }
    setErrorMessage(null);
  };

  return (
    <div className="manual-investigation-container">
      <div className="manual-header card">
        <div className="manual-title-row">
          <IconTerminal size={18} className="text-secondary" />
          <h2 className="section-heading">Manual Issue Investigation</h2>
        </div>
        <p className="section-lead">
          Directly investigate raw issue text, historical commits, or custom branch
          comparisons without requiring an open pull request.
        </p>

        <div className="demo-preset-row">
          <span className="preset-label">Load sample issue report:</span>
          <button
            type="button"
            className="chip-btn"
            onClick={() => handleLoadDemoCase('csv')}
          >
            Flask Unicode Query Parsing
          </button>
          <button
            type="button"
            className="chip-btn"
            onClick={() => handleLoadDemoCase('flask')}
          >
            Requests RFC 7230 Chunked
          </button>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="manual-form card mt-4">
        <div className="form-grid-2">
          <div className="form-group">
            <label htmlFor="manual-repo" className="form-label">
              Repository URL or owner/repo
            </label>
            <input
              id="manual-repo"
              type="text"
              className="form-input"
              value={repository}
              onChange={(e) => setRepository(e.target.value)}
              placeholder="e.g. pallets/flask or https://github.com/pallets/flask"
              disabled={isSubmitting}
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="manual-rev" className="form-label">
              Original Revision (SHA, branch, tag)
            </label>
            <input
              id="manual-rev"
              type="text"
              className="form-input font-mono"
              value={revision}
              onChange={(e) => setRevision(e.target.value)}
              placeholder="e.g. main or commit SHA"
              disabled={isSubmitting}
              required
            />
          </div>
        </div>

        <div className="form-group">
          <label htmlFor="manual-comp-rev" className="form-label">
            Comparison Revision (Optional proposed fix commit/branch)
          </label>
          <input
            id="manual-comp-rev"
            type="text"
            className="form-input font-mono"
            value={comparisonRevision}
            onChange={(e) => setComparisonRevision(e.target.value)}
            placeholder="e.g. fix-branch or 7e937d2..."
            disabled={isSubmitting}
          />
          <span className="input-hint">
            Enables side-by-side same-test reproduction if provided.
          </span>
        </div>

        <div className="form-group">
          <div className="form-label-row">
            <label htmlFor="manual-text" className="form-label">
              Issue or PR Report Text
            </label>
            <span className="form-label-hint">Max 12,000 characters</span>
          </div>
          <textarea
            id="manual-text"
            className="form-textarea"
            rows={8}
            value={reportText}
            onChange={(e) => setReportText(e.target.value)}
            placeholder="Paste issue reproduction description, stack traces, and technical claims..."
            disabled={isSubmitting}
            required
          />
        </div>

        {errorMessage && (
          <div className="callout callout-error" role="alert">
            <IconAlertCircle size={16} className="callout-icon" />
            <div className="callout-content">{errorMessage}</div>
          </div>
        )}

        <div className="form-actions">
          <button
            type="submit"
            className="btn btn-primary"
            disabled={isSubmitting || !reportText.trim()}
          >
            {isSubmitting ? (
              <IconRefresh size={14} className="spin" />
            ) : (
              <IconPlay size={14} />
            )}
            <span>Start Investigation</span>
          </button>
        </div>
      </form>
    </div>
  );
}

