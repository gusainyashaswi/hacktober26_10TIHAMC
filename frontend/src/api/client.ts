import {
  AnalysisReport,
  AnalysisRequest,
  AcceptedAnalysis,
  VerificationPlan,
} from '../types/analysis';
import {
  ConnectedRepository,
  HealthResponse,
  InvestigationRecord,
  PullDetail,
  PullsResponse,
} from '../types/repository';

export const API_BASE =
  import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

export class ApiError extends Error {
  status: number;
  data: unknown;

  constructor(message: string, status: number, data?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

async function handleResponse<T>(
  response: Response,
  fallbackError: string,
): Promise<T> {
  if (!response.ok) {
    let detail = `${fallbackError} (status ${response.status})`;
    let data: unknown = null;
    try {
      const errJson = await response.json();
      data = errJson;
      if (errJson.detail) {
        if (typeof errJson.detail === 'string') {
          detail = errJson.detail;
        } else if (Array.isArray(errJson.detail)) {
          detail = errJson.detail
            .map((e: { msg?: string }) => e.msg || JSON.stringify(e))
            .join('; ');
        } else {
          detail = JSON.stringify(errJson.detail);
        }
      }
    } catch {
      // Body not JSON
    }
    throw new ApiError(detail, response.status, data);
  }

  if (response.status === 204) {
    return undefined as unknown as T;
  }

  return response.json();
}

// 1. Health check
export async function fetchHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE}/api/health`, {
    headers: { Accept: 'application/json' },
  });
  return handleResponse<HealthResponse>(response, 'Health check failed');
}

// 2. Repositories
export async function fetchRepositories(): Promise<ConnectedRepository[]> {
  const response = await fetch(`${API_BASE}/api/repositories`, {
    headers: { Accept: 'application/json' },
  });
  const data = await handleResponse<{ items: ConnectedRepository[] }>(
    response,
    'Failed to load connected repositories',
  );
  return data.items;
}

export async function connectRepository(
  repository: string,
): Promise<ConnectedRepository> {
  const response = await fetch(`${API_BASE}/api/repositories`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify({ repository }),
  });
  return handleResponse<ConnectedRepository>(
    response,
    'Failed to connect repository',
  );
}

export async function disconnectRepository(id: number): Promise<void> {
  const response = await fetch(`${API_BASE}/api/repositories/${id}`, {
    method: 'DELETE',
    headers: { Accept: 'application/json' },
  });
  return handleResponse<void>(response, 'Failed to disconnect repository');
}

// 3. Pull Requests
export async function fetchPullRequests(
  repositoryId: number,
  page: number = 1,
): Promise<PullsResponse> {
  const response = await fetch(
    `${API_BASE}/api/repositories/${repositoryId}/pulls?page=${page}`,
    {
      headers: { Accept: 'application/json' },
    },
  );
  return handleResponse<PullsResponse>(
    response,
    `Failed to load pull requests for repository #${repositoryId}`,
  );
}

export async function fetchPullRequestDetail(
  repositoryId: number,
  prNumber: number,
): Promise<PullDetail> {
  const response = await fetch(
    `${API_BASE}/api/repositories/${repositoryId}/pulls/${prNumber}`,
    {
      headers: { Accept: 'application/json' },
    },
  );
  return handleResponse<PullDetail>(
    response,
    `Failed to load pull request #${prNumber}`,
  );
}

// 4. Analyse Pull Request (Backend resolves merge base & pinned context!)
export async function submitPRAnalysis(
  repositoryId: number,
  prNumber: number,
): Promise<AcceptedAnalysis> {
  const response = await fetch(
    `${API_BASE}/api/repositories/${repositoryId}/pulls/${prNumber}/analyses`,
    {
      method: 'POST',
      headers: {
        Accept: 'application/json',
      },
    },
  );
  return handleResponse<AcceptedAnalysis>(
    response,
    `Failed to submit analysis for PR #${prNumber}`,
  );
}

// 5. Investigations & History (persisted in backend SQLite)
export async function fetchInvestigations(
  repositoryId?: number,
): Promise<InvestigationRecord[]> {
  const url =
    repositoryId !== undefined
      ? `${API_BASE}/api/repositories/${repositoryId}/investigations`
      : `${API_BASE}/api/investigations`;

  const response = await fetch(url, {
    headers: { Accept: 'application/json' },
  });
  const data = await handleResponse<{ items: InvestigationRecord[] }>(
    response,
    'Failed to load investigations history',
  );
  return data.items;
}

// 6. Generic Analysis (Manual Investigation)
export async function submitAnalysis(
  request: AnalysisRequest,
): Promise<AcceptedAnalysis> {
  const response = await fetch(`${API_BASE}/api/analyses`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify(request),
  });
  return handleResponse<AcceptedAnalysis>(response, 'Analysis submission failed');
}

export async function fetchAnalysis(id: string): Promise<AnalysisReport> {
  const response = await fetch(
    `${API_BASE}/api/analyses/${encodeURIComponent(id)}`,
    {
      headers: { Accept: 'application/json' },
    },
  );
  return handleResponse<AnalysisReport>(
    response,
    `Failed to fetch analysis ${id}`,
  );
}

export function getExportUrl(id: string, format: 'json' | 'markdown'): string {
  return `${API_BASE}/api/analyses/${encodeURIComponent(id)}/export?format=${format}`;
}

// 7. Controlled Verification & Comparison
export async function submitVerification(
  id: string,
  plan: VerificationPlan,
): Promise<{ analysis_id: string; status: string }> {
  const response = await fetch(
    `${API_BASE}/api/analyses/${encodeURIComponent(id)}/verification`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body: JSON.stringify(plan),
    },
  );
  return handleResponse<{ analysis_id: string; status: string }>(
    response,
    'Verification submission failed',
  );
}

export async function submitComparison(
  id: string,
  plan: VerificationPlan,
): Promise<{ analysis_id: string; status: string }> {
  const response = await fetch(
    `${API_BASE}/api/analyses/${encodeURIComponent(id)}/comparison`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body: JSON.stringify(plan),
    },
  );
  return handleResponse<{ analysis_id: string; status: string }>(
    response,
    'Comparison submission failed',
  );
}
