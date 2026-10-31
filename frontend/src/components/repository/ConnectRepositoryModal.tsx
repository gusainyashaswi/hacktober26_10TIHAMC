import React, { useState } from 'react';
import { ConnectedRepository } from '../../types/repository';
import {
  devConnectRepository,
  parseRepositoryInput,
} from '../../api/devAdapter';
import {
  IconAlertCircle,
  IconCheck,
  IconRefresh,
  IconRepo,
  IconShield,
  IconX,
} from '../common/Icons';

interface ConnectRepositoryModalProps {
  isOpen: boolean;
  onClose?: () => void;
  onConnected: (repo: ConnectedRepository) => void;
  isInitialSetup?: boolean;
}

type ConnectState =
  | 'idle'
  | 'validating'
  | 'connecting'
  | 'connected'
  | 'error';

export function ConnectRepositoryModal({
  isOpen,
  onClose,
  onConnected,
  isInitialSetup = false,
}: ConnectRepositoryModalProps) {
  const [input, setInput] = useState('');
  const [state, setState] = useState<ConnectState>('idle');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [errorType, setErrorType] = useState<string | null>(null);
  const [connectedRepo, setConnectedRepo] = useState<ConnectedRepository | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed) {
      setErrorType('unsupported_url');
      setErrorMessage('Please enter a repository in owner/repo format or a valid GitHub URL.');
      return;
    }

    const parsed = parseRepositoryInput(trimmed);
    if (!parsed) {
      setErrorType('unsupported_url');
      setErrorMessage(
        'Unsupported repository format. Please use "owner/repository" or "https://github.com/owner/repository".',
      );
      return;
    }

    setState('validating');
    setErrorMessage(null);
    setErrorType(null);

    try {
      setState('connecting');
      // Connect repository via adapter or backend
      const result = await devConnectRepository(trimmed);
      setState('connected');
      setConnectedRepo(result.repository);

      setTimeout(() => {
        onConnected(result.repository);
        if (onClose) onClose();
      }, 700);
    } catch (err: unknown) {
      setState('error');
      const msg = err instanceof Error ? err.message : String(err);
      if (msg.includes('rate-limit') || msg.includes('rate limit')) {
        setErrorType('rate_limit');
        setErrorMessage('GitHub API rate limit encountered. Please try again later.');
      } else if (msg.includes('private') || msg.includes('authentication')) {
        setErrorType('private_repo');
        setErrorMessage(
          'Private repository or authentication required. Backend GitHub token integration is not active.',
        );
      } else if (msg.includes('not found') || msg.includes('404')) {
        setErrorType('not_found');
        setErrorMessage('Repository not found. Check the owner and repository name.');
      } else if (msg.includes('backend') || msg.includes('NetworkError')) {
        setErrorType('backend_unavailable');
        setErrorMessage('Backend connection unavailable. Is the NoBluff API server running?');
      } else {
        setErrorType('unsupported_url');
        setErrorMessage(msg);
      }
    }
  };

  const handlePresetSelect = (preset: string) => {
    setInput(preset);
  };

  return (
    <div
      className="modal-backdrop"
      role="dialog"
      aria-modal="true"
      aria-labelledby="connect-repo-title"
    >
      <div className="modal-card connect-modal">
        <div className="modal-header">
          <div className="modal-title-wrap">
            <IconRepo size={18} className="text-secondary" />
            <h2 id="connect-repo-title" className="modal-title">
              Connect Repository
            </h2>
          </div>
          {!isInitialSetup && onClose && (
            <button
              type="button"
              className="btn-icon"
              onClick={onClose}
              aria-label="Close modal"
            >
              <IconX size={16} />
            </button>
          )}
        </div>

        <p className="modal-lead">
          NoBluff extracts technical claims from pull requests and validates them
          against pinned repository source and controlled test executions.
        </p>

        <form onSubmit={handleSubmit} className="connect-form">
          <div className="form-group">
            <label htmlFor="repo-input" className="form-label">
              GitHub Repository
            </label>
            <div className="input-with-hint">
              <input
                id="repo-input"
                type="text"
                className={`form-input ${state === 'error' ? 'input-error' : ''}`}
                placeholder="e.g. pallets/flask or https://github.com/pallets/flask"
                value={input}
                onChange={(e) => {
                  setInput(e.target.value);
                  if (state === 'error') {
                    setState('idle');
                    setErrorMessage(null);
                  }
                }}
                disabled={state === 'validating' || state === 'connecting' || state === 'connected'}
                autoFocus
              />
              <span className="input-hint">
                Accepts <code className="code-inline">owner/repo</code> or full GitHub URL.
              </span>
            </div>
          </div>

          <div className="preset-suggestions">
            <span className="preset-label">Suggested demo repositories:</span>
            <div className="preset-chips">
              <button
                type="button"
                className="chip-btn"
                onClick={() => handlePresetSelect('pallets/flask')}
              >
                pallets/flask
              </button>
              <button
                type="button"
                className="chip-btn"
                onClick={() => handlePresetSelect('psf/requests')}
              >
                psf/requests
              </button>
            </div>
          </div>

          <div className="callout callout-info">
            <IconShield size={16} className="callout-icon" />
            <div className="callout-content">
              <strong>Public repositories supported:</strong> Open PRs will be
              indexed automatically. Private repositories require backend GitHub
              App credentials which are currently not enabled.
            </div>
          </div>

          {state === 'error' && errorMessage && (
            <div
              className="callout callout-error"
              role="alert"
              data-error-type={errorType}
            >
              <IconAlertCircle size={16} className="callout-icon" />
              <div className="callout-content">{errorMessage}</div>
            </div>
          )}

          {state === 'connected' && connectedRepo && (
            <div className="callout callout-success" role="status">
              <IconCheck size={16} className="callout-icon" />
              <div className="callout-content">
                Connected to <strong>{connectedRepo.fullName}</strong>. Loading PR inbox...
              </div>
            </div>
          )}

          <div className="modal-actions">
            {!isInitialSetup && onClose && (
              <button
                type="button"
                className="btn btn-secondary"
                onClick={onClose}
                disabled={state === 'validating' || state === 'connecting'}
              >
                Cancel
              </button>
            )}
            <button
              type="submit"
              className="btn btn-primary"
              disabled={
                !input.trim() ||
                state === 'validating' ||
                state === 'connecting' ||
                state === 'connected'
              }
            >
              {(state === 'validating' || state === 'connecting') && (
                <IconRefresh size={14} className="spin" />
              )}
              {state === 'validating'
                ? 'Validating repository...'
                : state === 'connecting'
                ? 'Connecting...'
                : state === 'connected'
                ? 'Connected'
                : 'Connect repository'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
