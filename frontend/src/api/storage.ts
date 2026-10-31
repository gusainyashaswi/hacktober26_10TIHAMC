import { ConnectedRepository, PullRequest } from '../types/repository';
import { AnalysisReport } from '../types/analysis';

const STORAGE_KEYS = {
  CONNECTED_REPOSITORIES: 'nobluff:connected_repos',
  SELECTED_REPO_ID: 'nobluff:selected_repo_id',
  PR_ANALYSIS_MAP: 'nobluff:pr_analysis_map',
  INVESTIGATION_HISTORY: 'nobluff:investigations_history',
  DEV_MODE_ENABLED: 'nobluff:dev_adapter_enabled',
};

export interface StoredInvestigation {
  id: string;
  repository: string;
  revision: string;
  comparison_revision?: string | null;
  prNumber?: number;
  prTitle?: string;
  createdAt: string;
  stage: string;
  claimCount: number;
  findingCount: number;
  executionCount: number;
}

export function getSavedRepositories(): ConnectedRepository[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEYS.CONNECTED_REPOSITORIES);
    if (!raw) return [];
    return JSON.parse(raw);
  } catch {
    return [];
  }
}

export function saveConnectedRepositories(repos: ConnectedRepository[]): void {
  try {
    localStorage.setItem(STORAGE_KEYS.CONNECTED_REPOSITORIES, JSON.stringify(repos));
  } catch {
    // Local storage unavailable or full
  }
}

export function getSelectedRepoId(): string | null {
  try {
    return localStorage.getItem(STORAGE_KEYS.SELECTED_REPO_ID);
  } catch {
    return null;
  }
}

export function saveSelectedRepoId(id: string | null): void {
  try {
    if (id) {
      localStorage.setItem(STORAGE_KEYS.SELECTED_REPO_ID, id);
    } else {
      localStorage.removeItem(STORAGE_KEYS.SELECTED_REPO_ID);
    }
  } catch {
    // Ignore
  }
}

export interface PRAnalysisRecord {
  analysisId: string;
  analysedHeadCommit: string;
  status: 'queued' | 'analysing' | 'complete' | 'failed' | 'outdated';
  updatedAt: string;
}

export function getPRAnalysisMap(repoId: string): Record<number, PRAnalysisRecord> {
  try {
    const raw = localStorage.getItem(`${STORAGE_KEYS.PR_ANALYSIS_MAP}:${repoId}`);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

export function updatePRAnalysis(
  repoId: string,
  prNumber: number,
  record: PRAnalysisRecord,
): void {
  try {
    const current = getPRAnalysisMap(repoId);
    current[prNumber] = record;
    localStorage.setItem(
      `${STORAGE_KEYS.PR_ANALYSIS_MAP}:${repoId}`,
      JSON.stringify(current),
    );
  } catch {
    // Ignore
  }
}

export function getInvestigationHistory(repoId?: string): StoredInvestigation[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEYS.INVESTIGATION_HISTORY);
    if (!raw) return [];
    const list: StoredInvestigation[] = JSON.parse(raw);
    if (repoId) {
      return list.filter((item) => item.repository === repoId || item.repository.includes(repoId));
    }
    return list;
  } catch {
    return [];
  }
}

export function recordInvestigation(
  report: AnalysisReport,
  pr?: PullRequest,
): void {
  try {
    const history = getInvestigationHistory();
    const existingIndex = history.findIndex((h) => h.id === report.id);
    const item: StoredInvestigation = {
      id: report.id,
      repository: report.repository,
      revision: report.revision,
      comparison_revision: report.comparison_revision,
      prNumber: pr?.number,
      prTitle: pr?.title,
      createdAt: new Date().toISOString(),
      stage: report.stage,
      claimCount: report.claims.length,
      findingCount: report.findings.length,
      executionCount: report.executions.length,
    };

    if (existingIndex >= 0) {
      history[existingIndex] = item;
    } else {
      history.unshift(item);
    }
    // Bound history to 50 items
    localStorage.setItem(
      STORAGE_KEYS.INVESTIGATION_HISTORY,
      JSON.stringify(history.slice(0, 50)),
    );
  } catch {
    // Ignore
  }
}

export function isDevAdapterDefaultEnabled(): boolean {
  try {
    const val = localStorage.getItem(STORAGE_KEYS.DEV_MODE_ENABLED);
    // Default to true for easy out-of-the-box exploration when backend PR endpoints are pending
    return val === null ? true : val === 'true';
  } catch {
    return true;
  }
}

export function setDevAdapterEnabled(enabled: boolean): void {
  try {
    localStorage.setItem(STORAGE_KEYS.DEV_MODE_ENABLED, enabled ? 'true' : 'false');
  } catch {
    // Ignore
  }
}

