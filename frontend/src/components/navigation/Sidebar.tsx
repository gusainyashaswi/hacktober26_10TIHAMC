import { useState } from 'react';
import { ConnectedRepository, HealthResponse } from '../../types/repository';
import {
  IconCheck,
  IconChevronDown,
  IconClock,
  IconGitPullRequest,
  IconRepo,
  IconSettings,
  IconTerminal,
} from '../common/Icons';

export type AppView = 'inbox' | 'pr_detail' | 'manual' | 'history' | 'investigation';

interface SidebarProps {
  currentView: AppView;
  connectedRepositories: ConnectedRepository[];
  selectedRepository: ConnectedRepository | null;
  health: HealthResponse | null;
  isDevMode: boolean;
  onNavigate: (view: AppView) => void;
  onSelectRepository: (repoId: number) => void;
  onOpenConnectModal: () => void;
  onOpenSettingsModal: () => void;
}

export function Sidebar({
  currentView,
  connectedRepositories,
  selectedRepository,
  health,
  isDevMode,
  onNavigate,
  onSelectRepository,
  onOpenConnectModal,
  onOpenSettingsModal,
}: SidebarProps) {
  const [repoDropdownOpen, setRepoDropdownOpen] = useState(false);

  return (
    <aside className="sidebar" aria-label="Main Navigation">
      {/* Wordmark and App Identity */}
      <div className="sidebar-brand">
        <div className="brand-title-wrap">
          <span className="brand-logo-mark" aria-hidden="true" />
          <h1 className="brand-wordmark">NoBluff</h1>
        </div>
        <p className="brand-subtitle">Evidence-Based Triage</p>
      </div>

      {/* Connected Repository Selector */}
      <div className="repo-selector-container">
        <button
          type="button"
          className="repo-selector-button"
          onClick={() => setRepoDropdownOpen(!repoDropdownOpen)}
          aria-expanded={repoDropdownOpen}
          aria-haspopup="listbox"
          title={selectedRepository ? selectedRepository.full_name : 'Connect repository'}
        >
          <IconRepo size={15} className="repo-icon" />
          <div className="repo-selector-text">
            <span className="selector-label">Repository</span>
            <span className="selector-current">
              {selectedRepository ? selectedRepository.full_name : 'Connect repo...'}
            </span>
          </div>
          <IconChevronDown size={14} className="dropdown-arrow" />
        </button>

        {repoDropdownOpen && (
          <div className="repo-dropdown-menu" role="listbox">
            <div className="dropdown-header">Connected Repositories</div>
            {connectedRepositories.map((repo) => (
              <button
                key={repo.id}
                type="button"
                role="option"
                aria-selected={selectedRepository?.id === repo.id}
                className={`repo-dropdown-item ${
                  selectedRepository?.id === repo.id ? 'active' : ''
                }`}
                onClick={() => {
                  onSelectRepository(repo.id);
                  setRepoDropdownOpen(false);
                }}
              >
                <span className="item-name">{repo.full_name}</span>
                {selectedRepository?.id === repo.id && (
                  <IconCheck size={12} className="text-forest" />
                )}
              </button>
            ))}

            <div className="dropdown-divider" />
            <button
              type="button"
              className="repo-dropdown-action"
              onClick={() => {
                setRepoDropdownOpen(false);
                onOpenConnectModal();
              }}
            >
              + Connect another repository
            </button>
          </div>
        )}
      </div>

      {/* Navigation Links */}
      <nav className="sidebar-nav">
        <ul className="nav-list">
          <li>
            <button
              type="button"
              className={`nav-item ${
                currentView === 'inbox' || currentView === 'pr_detail' ? 'active' : ''
              }`}
              onClick={() => onNavigate('inbox')}
            >
              <IconGitPullRequest size={16} />
              <span>Pull Requests</span>
            </button>
          </li>
          <li>
            <button
              type="button"
              className={`nav-item ${currentView === 'manual' ? 'active' : ''}`}
              onClick={() => onNavigate('manual')}
            >
              <IconTerminal size={16} />
              <span>Manual Investigation</span>
            </button>
          </li>
          <li>
            <button
              type="button"
              className={`nav-item ${currentView === 'history' ? 'active' : ''}`}
              onClick={() => onNavigate('history')}
            >
              <IconClock size={16} />
              <span>Investigations</span>
            </button>
          </li>
          <li>
            <button
              type="button"
              className="nav-item"
              onClick={onOpenSettingsModal}
            >
              <IconSettings size={16} />
              <span>Settings</span>
            </button>
          </li>
        </ul>
      </nav>

      {/* Footer Service Status Indicator */}
      <div className="sidebar-footer">
        {isDevMode && (
          <div className="dev-mode-pill" title="Using isolated development adapter fixtures">
            <span>Adapter Mode</span>
          </div>
        )}

        <button
          type="button"
          className="service-status-pill"
          onClick={onOpenSettingsModal}
          title="Click to inspect service status"
        >
          <span
            className={`status-dot ${health ? 'status-dot-ok' : 'status-dot-offline'}`}
          />
          <span className="status-label">
            {health ? health.model : 'Backend Offline'}
          </span>
        </button>
      </div>
    </aside>
  );
}
