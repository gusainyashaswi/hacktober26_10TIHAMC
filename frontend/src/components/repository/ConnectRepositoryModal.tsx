import React, { useState } from 'react';
import { ConnectedRepository } from '../../types/repository';
import { connectRepository, ApiError } from '../../api/client';
import { devConnectRepository } from '../../api/devAdapter';
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
  isDevMode?: boolean;
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
  isDevMode = false,
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

    setState('validating');
    setErrorMessage(null);
    setErrorType(null);

    try {
      setState('connecting');
      let repo: ConnectedRepository;

      if (isDevMode) {
        const result = await devConnectRepository(trimmed);
        repo = result.repository;
      } else {
        repo = await connectRepository(trimmed);
      }

      setState('connected');
      setConnectedRepo(repo);

      setTimeout(() => {
        onConnected(repo);
        if (onClose) onClose();
      }, 500);
    } catch (err: unknown) {
      setState('error');
      if (err instanceof ApiError) {
        if (err.status === 409) {
          setErrorType('limit_reached');
          setErrorMessage('Repository limit reached: maximum 20 repositories connected. Disconnect a repository before adding more.');
        } else if (err.status === 404) {
          setErrorType('not_found');
          setErrorMessage('Repository not found on GitHub. Check the owner and repository name.');
        } else if (err.status === 422) {
          if (err.message.toLowerCase().includes('private')) {
            setErrorType('private_repo');
            setErrorMessage('Only public repositories are supported. Private repositories and credentials are not supported.');
          } else {
            setErrorType('unsupported_url');
            setErrorMessage(err.message || 'Invalid repository format. Use owner/repository or https://github.com/owner/repository.');
          }
        } else if (err.status === 429) {
          setErrorType('rate_limit');
          setErrorMessage('GitHub access is restricted or rate-limited. Try later or configure a server-side token.');
        } else if (err.status === 502) {
          setErrorType('gateway_error');
          setErrorMessage(err.message || 'GitHub could not provide repository metadata. Redirected repository names must be reconnected.');
        } else {
          setErrorType('generic_error');
          setErrorMessage(err.message || 'Failed to connect repository.');
        }
      } else {
        const msg = err instanceof Error ? err.message : String(err);
        if (msg.includes('Failed to fetch') || msg.includes('NetworkError') || msg.includes('connection refused')) {
          setErrorType('backend_unavailable');
          setErrorMessage('Backend connection unavailable. Is the NoBluff API server running at http://127.0.0.1:8000?');
        } else {
          setErrorType('generic_error');
          setErrorMessage(msg);
        }
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
                Accepts <code className="code-inline">owner/repo</code> or canonical public GitHub URL.
              </span>
            </div>
          </div>

          <div className="preset-suggestions">
            <span className="preset-label">Suggested public repositories:</span>
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
              <strong>Public GitHub repositories only:</strong> Open PRs will be
              indexed through the NoBluff backend SQLite workspace. Private repositories
              and credentials are not supported.
            </div>
          </div>

          {state === 'error' && errorMessage && (
            <div
              className="callout callout-error"
              role="alert"
              data-error-type={errorType}
            >
              <IconAlertCircle size={16} className="callout-icon" />
              <div className="callout-content">
                <div>{errorMessage}</div>
                {errorType === 'rate_limit' && (
                  <div style={{ marginTop: '0.5rem' }}>
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      onClick={async () => {
                        try {
                          setState('connecting');
                          setErrorMessage(null);
                          const result = await devConnectRepository(input.trim());
                          setState('connected');
                          setConnectedRepo(result.repository);
                          setTimeout(() => {
                            onConnected(result.repository);
                            if (onClose) onClose();
                          }, 500);
                        } catch (devErr: unknown) {
                          setState('error');
                          setErrorMessage(
                            devErr instanceof Error ? devErr.message : String(devErr),
                          );
                        }
                      }}
                    >
                      Connect with offline fixture
                    </button>
                  </div>
                )}
              </div>
            </div>
          )}

          {state === 'connected' && connectedRepo && (
            <div className="callout callout-success" role="status">
              <IconCheck size={16} className="callout-icon" />
              <div className="callout-content">
                Connected to <strong>{connectedRepo.full_name}</strong>. Loading PR inbox...
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
                ? 'Connecting to backend...'
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
