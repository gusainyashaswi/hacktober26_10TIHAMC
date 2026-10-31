import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  fetchHealth,
  submitAnalysis,
  fetchAnalysis,
  getExportUrl,
  submitVerification,
  submitComparison,
  ApiError,
} from './client';

describe('Typed API Client', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('fetchHealth returns typed health status', async () => {
    const mockHealth = {
      status: 'ok',
      scope: 'source_review',
      model: 'qwen3:8b',
      model_readiness: 'ready',
      repository_loading: true,
      evidence_assessment: true,
      verification: true,
    };

    vi.spyOn(global, 'fetch').mockResolvedValueOnce({
      ok: true,
      json: async () => mockHealth,
    } as Response);

    const data = await fetchHealth();
    expect(data.scope).toBe('source_review');
    expect(data.verification).toBe(true);
  });

  it('submitAnalysis handles 422 validation errors with sanitized detail message', async () => {
    vi.spyOn(global, 'fetch').mockResolvedValueOnce({
      ok: false,
      status: 422,
      json: async () => ({
        detail: 'Use a public GitHub repository URL or owner/repository',
      }),
    } as unknown as Response);

    await expect(
      submitAnalysis({
        repository: 'invalid/local/path',
        revision: 'main',
        report_text: 'sample',
      }),
    ).rejects.toThrow(ApiError);
  });

  it('fetchAnalysis returns report on 200 and raises ApiError on 404', async () => {
    vi.spyOn(global, 'fetch').mockResolvedValueOnce({
      ok: false,
      status: 404,
      json: async () => ({ detail: 'Analysis not found in this server process.' }),
    } as unknown as Response);

    await expect(fetchAnalysis('missing-id')).rejects.toThrow(ApiError);
  });

  it('getExportUrl builds correct download URLs for JSON and Markdown', () => {
    expect(getExportUrl('test-1', 'json')).toContain('/api/analyses/test-1/export?format=json');
    expect(getExportUrl('test-1', 'markdown')).toContain('/api/analyses/test-1/export?format=markdown');
  });

  it('submitVerification handles 501 disabled container verification', async () => {
    vi.spyOn(global, 'fetch').mockResolvedValueOnce({
      ok: false,
      status: 501,
      json: async () => ({
        detail: 'Controlled verification is disabled. No code was executed.',
      }),
    } as unknown as Response);

    await expect(
      submitVerification('test-1', {
        claim_id: 'c1',
        test_code: 'def test(): pass',
        approved: true,
      }),
    ).rejects.toThrow(/Controlled verification is disabled/i);
  });

  it('submitComparison posts to comparison endpoint with approved flag', async () => {
    const fetchSpy = vi.spyOn(global, 'fetch').mockResolvedValueOnce({
      ok: true,
      status: 202,
      json: async () => ({ analysis_id: 'test-1', status: 'comparison_accepted' }),
    } as Response);

    const result = await submitComparison('test-1', {
      claim_id: 'c1',
      test_code: 'def test(): pass',
      approved: true,
    });

    expect(result.status).toBe('comparison_accepted');
    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining('/api/analyses/test-1/comparison'),
      expect.objectContaining({
        method: 'POST',
      }),
    );
  });
});
