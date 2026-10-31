export type Assessment = 'supported' | 'contradicted' | 'inconclusive';

export type ExecutionStatus =
  | 'not_run'
  | 'passed'
  | 'failed'
  | 'setup_error'
  | 'timeout'
  | 'blocked';

export type Stage =
  | 'queued'
  | 'loading'
  | 'extracting'
  | 'awaiting_evidence'
  | 'retrieving'
  | 'assessing'
  | 'awaiting_verification'
  | 'verifying'
  | 'complete'
  | 'error';

export interface AnalysisRequest {
  repository: string;
  revision: string;
  report_text: string;
  comparison_revision?: string | null;
}

export type ClaimKind = 'behavior' | 'cause' | 'documentation' | 'fix' | 'other';

export interface Claim {
  id: string;
  text: string;
  kind: ClaimKind;
  search_terms: string[];
  reported_as: 'assertion' | 'hypothesis';
}

export type EvidenceKind = 'source' | 'documentation' | 'test' | 'execution';

export interface Evidence {
  id: string;
  kind: EvidenceKind;
  revision: string;
  path?: string | null;
  start_line?: number | null;
  end_line?: number | null;
  excerpt: string;
  execution_id?: string | null;
}

export interface Finding {
  claim_id: string;
  assessment: Assessment;
  evidence_ids: string[];
  explanation: string;
  limitations: string[];
  suggested_next_step?: string | null;
}

export interface ExecutionResult {
  id: string;
  revision: string;
  test_hash: string;
  command: string[];
  environment: Record<string, string>;
  status: ExecutionStatus;
  exit_code?: number | null;
  stdout: string;
  stderr: string;
  duration_ms: number;
}

export interface ApprovedTest {
  claim_id: string;
  test_hash: string;
  test_code: string;
  expected_failure?: string | null;
}

export type ComparisonStatus =
  | 'fix_verified_for_test'
  | 'not_reproduced_for_test'
  | 'still_failing'
  | 'inconclusive';

export interface ComparisonResult {
  claim_id: string;
  original_execution_id: string;
  comparison_execution_id: string;
  test_hash: string;
  status: ComparisonStatus;
  limitations: string[];
}

export interface AnalysisReport {
  schema_version: '1.0';
  is_example?: boolean;
  id: string;
  repository: string;
  revision: string;
  comparison_revision?: string | null;
  model: string;
  stage: Stage;
  claims: Claim[];
  evidence: Evidence[];
  findings: Finding[];
  executions: ExecutionResult[];
  approved_tests: ApprovedTest[];
  comparisons: ComparisonResult[];
  errors: string[];
}

export interface VerificationPlan {
  claim_id: string;
  test_code: string;
  approved: true;
  expected_failure?: string | null;
}

export interface AcceptedAnalysis {
  id: string;
}
