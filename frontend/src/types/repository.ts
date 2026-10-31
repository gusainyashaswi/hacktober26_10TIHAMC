export interface ConnectedRepository {
  id: string; // e.g. "owner/repo" or "https://github.com/owner/repo"
  owner: string;
  name: string;
  fullName: string;
  url: string;
  defaultBranch: string;
  isPrivate: boolean;
  connectedAt: string;
}

export type PRAnalysisStatus =
  | 'not_analysed'
  | 'queued'
  | 'analysing'
  | 'complete'
  | 'failed'
  | 'outdated';

export interface ChangedFileSummary {
  path: string;
  status: 'added' | 'modified' | 'removed' | 'renamed';
  additions: number;
  deletions: number;
}

export interface PullRequest {
  id: string;
  number: number;
  title: string;
  author: string;
  authorAvatarUrl?: string;
  sourceBranch: string;
  targetBranch: string;
  baseCommit: string;
  headCommit: string;
  updatedAt: string;
  createdAt: string;
  isDraft: boolean;
  htmlUrl: string;
  analysisState?: PRAnalysisStatus;
  lastAnalysisId?: string;
  lastAnalysedHeadCommit?: string;
}

export interface PullRequestDetail extends PullRequest {
  description: string;
  changedFiles: ChangedFileSummary[];
  totalAdditions: number;
  totalDeletions: number;
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

