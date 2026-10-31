export interface ConnectedRepository {
  id: number;
  full_name: string;
  url: string;
  default_branch: string;
  connected_at: string;
}

export type PRAnalysisStatus =
  | 'not_analysed'
  | 'queued'
  | 'analysing'
  | 'complete'
  | 'failed'
  | 'outdated';

export interface ChangedFilePatch {
  filename: string;
  status: string;
  additions: number;
  deletions: number;
  patch: string;
}

export interface PullComparisonContext {
  pr_number: number;
  title: string;
  url: string;
  head_sha: string;
  head_repository: string;
  base_tip_sha: string;
  comparison_basis: string;
  files: ChangedFilePatch[];
  diff_note: string;
}

export interface PRComparisonDetail {
  original_revision: string;
  head_revision: string;
  base_tip_revision: string;
  comparison_basis: string;
  files: ChangedFilePatch[];
  diff_note: string;
}

export interface PRHistoryEntry {
  id: string;
  created_at: string;
  repository: string;
  revision: string;
  comparison_revision: string | null;
  stage: string;
  context: PullComparisonContext;
  outdated: boolean;
}

export interface PullSummary {
  number: number;
  title: string;
  author: string;
  url: string;
  state: string;
  draft: boolean;
  updated_at: string;
  head_sha: string;
  base_sha: string;
  head_branch: string;
  base_branch: string;
  // Computed client-side display helper
  latest_analysis_id?: string;
  latest_analysis_stage?: string;
  is_outdated?: boolean;
}

export interface PullDetail extends PullSummary {
  head_repository: string;
  body: string;
  additions: number | null;
  deletions: number | null;
  changed_files: number | null;
  merged: boolean;
  history: PRHistoryEntry[];
}

export interface PullsResponse {
  items: PullSummary[];
  page: number;
  has_more: boolean;
  refreshed_at: string;
}

export interface InvestigationRecord {
  id: string;
  created_at: string;
  repository: string;
  revision: string;
  comparison_revision: string | null;
  stage: string;
  context: Partial<PullComparisonContext> & Record<string, unknown>;
}

export interface HealthResponse {
  status: string;
  scope: 'source_review' | 'claim_extraction' | string;
  model: string;
  model_readiness: 'not_checked' | 'ready' | 'error';
  repository_loading: boolean;
  evidence_assessment: boolean;
  verification: boolean;
}
