import {
  AnalysisReport,
  AnalysisRequest,
  AcceptedAnalysis,
  VerificationPlan,
} from '../types/analysis';
import { HealthResponse } from '../types/repository';

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

export async function fetchHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE}/api/health`, {
    headers: { Accept: 'application/json' },
  });
  if (!response.ok) {
    throw new ApiError(`Health check failed with status ${response.status}`, response.status);
  }
  return response.json();
}

export async function submitAnalysis(request: AnalysisRequest): Promise<AcceptedAnalysis> {
  const response = await fetch(`${API_BASE}/api/analyses`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    let detail = `Submission failed with status ${response.status}`;
    try {
      const errJson = await response.json();
      if (errJson.detail) {
        detail = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
      }
    } catch {
      // Keep default detail
    }
    throw new ApiError(detail, response.status);
  }

  return response.json();
}

export async function fetchAnalysis(id: string): Promise<AnalysisReport> {
  const response = await fetch(`${API_BASE}/api/analyses/${encodeURIComponent(id)}`, {
    headers: { Accept: 'application/json' },
  });

  if (!response.ok) {
    let detail = `Failed to fetch analysis ${id}`;
    try {
      const errJson = await response.json();
      if (errJson.detail) {
        detail = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
      }
    } catch {
      // Keep default
    }
    throw new ApiError(detail, response.status);
  }

  return response.json();
}

export function getExportUrl(id: string, format: 'json' | 'markdown'): string {
  return `${API_BASE}/api/analyses/${encodeURIComponent(id)}/export?format=${format}`;
}

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

  if (!response.ok) {
    let detail = `Verification submission failed with status ${response.status}`;
    try {
      const errJson = await response.json();
      if (errJson.detail) {
        detail = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
      }
    } catch {
      // Keep default
    }
    throw new ApiError(detail, response.status);
  }

  return response.json();
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

  if (!response.ok) {
    let detail = `Comparison submission failed with status ${response.status}`;
    try {
      const errJson = await response.json();
      if (errJson.detail) {
        detail = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
      }
    } catch {
      // Keep default
    }
    throw new ApiError(detail, response.status);
  }

  return response.json();
}
