import { useState } from 'react';
import { ConnectedRepository, HealthResponse } from '../../types/repository';
import {
  IconAlertCircle,
  IconCheck,
  IconRefresh,
  IconRepo,
  IconSettings,
  IconShield,
  IconX,
} from '../common/Icons';

interface SettingsModalProps {
  isOpen: boolean;
  connectedRepositories: ConnectedRepository[];
  selectedRepoId: number | null;
  health: HealthResponse | null;
  healthLoading: boolean;
  isDevMode: boolean;
  onClose: () => void;
  onRefreshHealth: () => void;
  onSelectRepo: (id: number) => void;
  onDisconnectRepo: (id: number) => void;
  onToggleDevMode: (enabled: boolean) => void;
  onConnectNewRepo: () => void;
}

export function SettingsModal({
  isOpen,
  connectedRepositories,
  selectedRepoId,
  health,
  healthLoading,
  isDevMode,
  onClose,
  onRefreshHealth,
  onSelectRepo,
  onDisconnectRepo,
  onToggleDevMode,
  onConnectNewRepo,
}: SettingsModalProps) {
  const [confirmDisconnectId, setConfirmDisconnectId] = useState<number | null>(null);

  if (!isOpen) return null;

  return (
    <div
      className="modal-backdrop"
      role="dialog"
      aria-modal="true"
      aria-labelledby="settings-title"
    >
      <div className="modal-card settings-modal">
        <header className="modal-header">
          <div className="modal-title-wrap">
            <IconSettings size={18} className="text-secondary" />
            <h2 id="settings-title" className="modal-title">
              Workspace Settings &amp; Service Status
            </h2>
          </div>
          <button
            type="button"
            className="btn-icon"
            onClick={onClose}
            aria-label="Close settings"
          >
            <IconX size={16} />
          </button>
        </header>

        <div className="settings-body">
          {/* Section 1: Connected Repositories */}
          <section className="settings-section">
            <div className="section-title-row">
              <h3 className="section-heading-sm">Connected Repositories</h3>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={onConnectNewRepo}
              >
                + Connect Repository
              </button>
            </div>

            {connectedRepositories.length === 0 ? (
              <p className="text-muted text-sm">No repositories connected yet.</p>
            ) : (
              <div className="repo-list">
                {connectedRepositories.map((repo) => {
                  const isSelected = selectedRepoId === repo.id;
                  const isConfirming = confirmDisconnectId === repo.id;

                  return (
                    <div
                      key={repo.id}
                      className={`repo-item-card ${isSelected ? 'selected' : ''}`}
                    >
                      <div className="repo-item-meta">
                        <IconRepo size={16} className="text-secondary" />
                        <div>
                          <div className="repo-item-title">
                            <strong>{repo.full_name}</strong>
                            {isSelected && (
                              <span className="badge badge-subtle ml-2">Active</span>
                            )}
                          </div>
                          <span className="repo-item-date text-muted">
                            Connected {new Date(repo.connected_at).toLocaleDateString()}
                          </span>
                        </div>
                      </div>

                      <div className="repo-item-actions">
                        {!isSelected && (
                          <button
                            type="button"
                            className="btn btn-secondary btn-sm"
                            onClick={() => onSelectRepo(repo.id)}
                          >
                            Switch to
                          </button>
                        )}

                        {isConfirming ? (
                          <div className="confirm-group">
                            <span className="confirm-text">Disconnect?</span>
                            <button
                              type="button"
                              className="btn btn-sm btn-danger"
                              onClick={() => {
                                onDisconnectRepo(repo.id);
                                setConfirmDisconnectId(null);
                              }}
                            >
                              Yes
                            </button>
                            <button
                              type="button"
                              className="btn btn-sm btn-secondary"
                              onClick={() => setConfirmDisconnectId(null)}
                            >
                              Cancel
                            </button>
                          </div>
                        ) : (
                          <button
                            type="button"
                            className="btn-text btn-text-danger"
                            onClick={() => setConfirmDisconnectId(repo.id)}
                          >
                            Disconnect
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </section>

          {/* Section 2: Service Status & Capabilities */}
          <section className="settings-section">
            <div className="section-title-row">
              <h3 className="section-heading-sm">Backend Service Status</h3>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={onRefreshHealth}
                disabled={healthLoading}
              >
                <IconRefresh size={12} className={healthLoading ? 'spin' : ''} />
                <span>Check Status</span>
              </button>
            </div>

            <div className="status-grid card">
              <div className="status-row">
                <span className="status-label">Backend Connection</span>
                <span className="status-val">
                  {health ? (
                    <span className="badge badge-supported">
                      <IconCheck size={11} /> Connected
                    </span>
                  ) : (
                    <span className="badge badge-contradicted">
                      <IconAlertCircle size={11} /> Offline
                    </span>
                  )}
                </span>
              </div>

              <div className="status-row">
                <span className="status-label">Configured Model</span>
                <span className="status-val">
                  <code>{health?.model || 'qwen3:8b'}</code>
                  <span className="text-muted ml-2 text-xs">
                    (readiness: {health?.model_readiness || 'not_checked'})
                  </span>
                </span>
              </div>

              <div className="status-row">
                <span className="status-label">Investigation Scope</span>
                <span className="status-val">
                  <span className="badge badge-neutral">
                    {health?.scope || 'claim_extraction'}
                  </span>
                </span>
              </div>

              <div className="status-row">
                <span className="status-label">Controlled Docker Verification</span>
                <span className="status-val">
                  {health?.verification ? (
                    <span className="badge badge-supported">
                      <IconShield size={11} /> Enabled
                    </span>
                  ) : (
                    <span className="badge badge-neutral">
                      Disabled (501)
                    </span>
                  )}
                </span>
              </div>
            </div>

            <p className="text-muted text-xs mt-2">
              Note: “Configured” indicates that server settings specify Qwen3-8B. Actual
              Ollama model responsiveness is evaluated upon submission.
            </p>
          </section>

          {/* Section 3: Development Adapter Mode */}
          <section className="settings-section">
            <h3 className="section-heading-sm">Development Adapter</h3>
            <div className="dev-mode-card card">
              <div className="dev-toggle-row">
                <div>
                  <strong>Isolated Development Adapter</strong>
                  <p className="text-muted text-xs">
                    Provides simulated pull request inboxes and commit fixtures for open-source repositories when backend GitHub integration is pending.
                  </p>
                </div>
                <label className="switch-label">
                  <input
                    type="checkbox"
                    checked={isDevMode}
                    onChange={(e) => onToggleDevMode(e.target.checked)}
                  />
                  <span className="switch-slider" />
                </label>
              </div>
            </div>
          </section>
        </div>

        <div className="modal-footer">
          <button
            type="button"
            className="btn btn-secondary"
            onClick={onClose}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
