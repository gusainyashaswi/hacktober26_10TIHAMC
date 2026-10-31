import { useCallback, useEffect, useRef, useState } from 'react';
import {
  AnalysisReport,
  AnalysisRequest,
  Evidence,
  VerificationPlan,
} from './types/analysis';
import {
  ConnectedRepository,
  HealthResponse,
  PullRequest,
  PullRequestDetail,
} from './types/repository';
import {
  fetchAnalysis,
  fetchHealth,
  getExportUrl,
  submitAnalysis,
  submitComparison,
  submitVerification,
} from './api/client';
import {
  devFetchPullRequestDetail,
  devFetchPullRequests,
} from './api/devAdapter';
import {
  getInvestigationHistory,
  getPRAnalysisMap,
  getSavedRepositories,
  getSelectedRepoId,
  isDevAdapterDefaultEnabled,
  recordInvestigation,
  saveConnectedRepositories,
  saveSelectedRepoId,
  setDevAdapterEnabled,
  updatePRAnalysis,
} from './api/storage';

import { AppView, Sidebar } from './components/navigation/Sidebar';
import { ConnectRepositoryModal } from './components/repository/ConnectRepositoryModal';
import { PullRequestInbox } from './components/inbox/PullRequestInbox';
import { PullRequestDetails } from './components/investigation/PullRequestDetails';
import { ManualInvestigation } from './components/investigation/ManualInvestigation';
import { InvestigationProgress } from './components/investigation/InvestigationProgress';
import { ClaimsList } from './components/investigation/ClaimsList';
import { EvidenceDrawer } from './components/evidence/EvidenceDrawer';
import { ReproductionForm } from './components/verification/ReproductionForm';
import { ExecutionResults } from './components/verification/ExecutionResults';
import { ComparisonView } from './components/verification/ComparisonView';
import { InvestigationHistory } from './components/history/InvestigationHistory';
import { SettingsModal } from './components/settings/SettingsModal';
import {
  IconArrowLeft,
  IconDownload,
  IconFileCode,
} from './components/common/Icons';

export default function App() {
  // Navigation & Repositories State
  const [connectedRepos, setConnectedRepos] = useState<ConnectedRepository[]>(
    () => getSavedRepositories(),
  );
  const [selectedRepoId, setSelectedRepoId] = useState<string | null>(() =>
    getSelectedRepoId(),
  );
  const [currentView, setCurrentView] = useState<AppView>('inbox');

  // Pull Requests State
  const [pullRequests, setPullRequests] = useState<PullRequest[]>([]);
  const [selectedPR, setSelectedPR] = useState<PullRequestDetail | null>(null);
  const [prLoading, setPrLoading] = useState(false);
  const [prError, setPrError] = useState<string | null>(null);
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);

  // Active Analysis State
  const [currentAnalysis, setCurrentAnalysis] = useState<AnalysisReport | null>(
    null,
  );
  const [isSubmittingAnalysis, setIsSubmittingAnalysis] = useState(false);
  const [isPolling, setIsPolling] = useState(false);
  const [pollCount, setPollCount] = useState(0);
  const pollingTimerRef = useRef<number | null>(null);

  // Evidence Drawer State
  const [selectedEvidence, setSelectedEvidence] = useState<Evidence | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  // Modals
  const [connectModalOpen, setConnectModalOpen] = useState(false);
  const [settingsModalOpen, setSettingsModalOpen] = useState(false);

  // Backend Health and Dev Mode
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthLoading, setHealthLoading] = useState(false);
  const [isDevMode, setIsDevMode] = useState<boolean>(() =>
    isDevAdapterDefaultEnabled(),
  );

  // Selected Repository Object
  const selectedRepository =
    connectedRepos.find((r) => r.id === selectedRepoId) ||
    connectedRepos[0] ||
    null;

  // Analysis map for current repo
  const currentAnalysisMap = selectedRepository
    ? getPRAnalysisMap(selectedRepository.id)
    : {};

  // Check backend health on mount
  const checkHealth = useCallback(async () => {
    setHealthLoading(true);
    try {
      const data = await fetchHealth();
      setHealth(data);
    } catch {
      setHealth(null);
    } finally {
      setHealthLoading(false);
    }
  }, []);

  useEffect(() => {
    checkHealth();
  }, [checkHealth]);

  // Load PRs when repository changes
  const loadPullRequests = useCallback(async (repo: ConnectedRepository) => {
    setPrLoading(true);
    setPrError(null);
    try {
      const prs = await devFetchPullRequests(repo.id);
      setPullRequests(prs);
      setLastRefreshed(new Date());
    } catch (err: unknown) {
      setPrError(err instanceof Error ? err.message : String(err));
    } finally {
      setPrLoading(false);
    }
  }, []);

  useEffect(() => {
    if (selectedRepository) {
      loadPullRequests(selectedRepository);
    } else {
      setPullRequests([]);
    }
  }, [selectedRepository, loadPullRequests]);

  // Polling management for active analysis
  const stopPolling = useCallback(() => {
    if (pollingTimerRef.current !== null) {
      window.clearInterval(pollingTimerRef.current);
      pollingTimerRef.current = null;
    }
    setIsPolling(false);
  }, []);

  useEffect(() => {
    return () => {
      stopPolling();
    };
  }, [stopPolling]);

  const pollAnalysis = useCallback(
    async (id: string) => {
      try {
        const report = await fetchAnalysis(id);
        setCurrentAnalysis(report);
        setPollCount((prev) => prev + 1);

        // Terminal stages check
        if (report.stage === 'complete' || report.stage === 'error') {
          stopPolling();

          // Record in persistent history
          recordInvestigation(report, selectedPR || undefined);

          // Update PR analysis map if tied to selected PR
          if (selectedRepository && selectedPR) {
            updatePRAnalysis(selectedRepository.id, selectedPR.number, {
              analysisId: report.id,
              analysedHeadCommit: selectedPR.headCommit,
              status: report.stage === 'complete' ? 'complete' : 'failed',
              updatedAt: new Date().toISOString(),
            });
          }
        }
      } catch (err: unknown) {
        // Preserving error without losing current context
        stopPolling();
      }
    },
    [selectedPR, selectedRepository, stopPolling],
  );

  const startPolling = useCallback(
    (id: string) => {
      stopPolling();
      setIsPolling(true);
      setPollCount(1);
      // Immediate initial fetch
      pollAnalysis(id);
      // Recurring poll every 2.5 seconds
      pollingTimerRef.current = window.setInterval(() => {
        pollAnalysis(id);
      }, 2500);
    },
    [pollAnalysis, stopPolling],
  );

  // Submit analysis workflow
  const handleStartAnalysis = async (request?: AnalysisRequest) => {
    setIsSubmittingAnalysis(true);
    try {
      let req: AnalysisRequest;

      if (request) {
        req = request;
      } else if (selectedRepository && selectedPR) {
        // Construct analysis request from PR metadata
        req = {
          repository: selectedRepository.url || `https://github.com/${selectedRepository.fullName}`,
          revision: selectedPR.baseCommit,
          comparison_revision: selectedPR.headCommit,
          report_text: `${selectedPR.title}\n\n${selectedPR.description}`,
        };
      } else {
        throw new Error('No repository or PR context available for analysis.');
      }

      const accepted = await submitAnalysis(req);

      // Create initial queued report state
      const initialReport: AnalysisReport = {
        schema_version: '1.0',
        id: accepted.id,
        repository: req.repository,
        revision: req.revision,
        comparison_revision: req.comparison_revision,
        model: health?.model || 'qwen3:8b',
        stage: 'queued',
        claims: [],
        evidence: [],
        findings: [],
        executions: [],
        approved_tests: [],
        comparisons: [],
        errors: [],
      };

      setCurrentAnalysis(initialReport);
      setCurrentView('investigation');

      if (selectedRepository && selectedPR) {
        updatePRAnalysis(selectedRepository.id, selectedPR.number, {
          analysisId: accepted.id,
          analysedHeadCommit: selectedPR.headCommit,
          status: 'analysing',
          updatedAt: new Date().toISOString(),
        });
      }

      startPolling(accepted.id);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : String(err));
    } finally {
      setIsSubmittingAnalysis(false);
    }
  };

  // Select PR from Inbox
  const handleSelectPR = async (pr: PullRequest) => {
    if (!selectedRepository) return;
    setPrLoading(true);
    try {
      const detail = await devFetchPullRequestDetail(selectedRepository.id, pr.number);
      setSelectedPR(detail);
      setCurrentView('pr_detail');
    } catch (err: unknown) {
      setPrError(err instanceof Error ? err.message : String(err));
    } finally {
      setPrLoading(false);
    }
  };

  // Reopen existing analysis
  const handleReopenAnalysis = async (analysisId: string) => {
    try {
      const report = await fetchAnalysis(analysisId);
      setCurrentAnalysis(report);
      setCurrentView('investigation');
      if (report.stage !== 'complete' && report.stage !== 'error') {
        startPolling(report.id);
      }
    } catch (err: unknown) {
      alert(`Could not open analysis ${analysisId}: ${err instanceof Error ? err.message : String(err)}`);
    }
  };

  // Open Evidence Drawer
  const handleOpenEvidence = (evidenceId: string) => {
    if (!currentAnalysis) return;
    const ev = currentAnalysis.evidence.find((e) => e.id === evidenceId);
    if (ev) {
      setSelectedEvidence(ev);
      setDrawerOpen(true);
    }
  };

  // Submit Controlled Verification or Comparison
  const handleSubmitReproduction = async (
    plan: VerificationPlan,
    isComparison: boolean,
  ) => {
    if (!currentAnalysis) return;

    if (isComparison) {
      await submitComparison(currentAnalysis.id, plan);
    } else {
      await submitVerification(currentAnalysis.id, plan);
    }

    // Refresh immediately and resume polling
    startPolling(currentAnalysis.id);
  };

  // Connected Repositories Management
  const handleConnectedNewRepo = (repo: ConnectedRepository) => {
    const updated = [repo, ...connectedRepos.filter((r) => r.id !== repo.id)];
    setConnectedRepos(updated);
    saveConnectedRepositories(updated);
    setSelectedRepoId(repo.id);
    saveSelectedRepoId(repo.id);
    setCurrentView('inbox');
  };

  const handleDisconnectRepo = (repoId: string) => {
    const updated = connectedRepos.filter((r) => r.id !== repoId);
    setConnectedRepos(updated);
    saveConnectedRepositories(updated);
    if (selectedRepoId === repoId) {
      const nextId = updated[0]?.id || null;
      setSelectedRepoId(nextId);
      saveSelectedRepoId(nextId);
    }
  };

  const handleSelectRepo = (repoId: string) => {
    setSelectedRepoId(repoId);
    saveSelectedRepoId(repoId);
    setSelectedPR(null);
    setCurrentAnalysis(null);
    stopPolling();
    setCurrentView('inbox');
  };

  const handleToggleDevMode = (enabled: boolean) => {
    setIsDevMode(enabled);
    setDevAdapterEnabled(enabled);
  };

  // If no repository is connected, prompt with Connect Modal
  const isInitialSetup = connectedRepos.length === 0;

  return (
    <div className="app-shell">
      {/* Left Navigation */}
      <Sidebar
        currentView={currentView}
        connectedRepositories={connectedRepos}
        selectedRepository={selectedRepository}
        health={health}
        isDevMode={isDevMode}
        onNavigate={(view) => {
          stopPolling();
          setCurrentView(view);
        }}
        onSelectRepository={handleSelectRepo}
        onOpenConnectModal={() => setConnectModalOpen(true)}
        onOpenSettingsModal={() => setSettingsModalOpen(true)}
      />

      {/* Main Workspace Area */}
      <main className="app-main" id="main-content">
        {/* View 1: Pull Request Inbox */}
        {currentView === 'inbox' && selectedRepository && (
          <PullRequestInbox
            repository={selectedRepository}
            pullRequests={pullRequests}
            analysisMap={currentAnalysisMap}
            isLoading={prLoading}
            error={prError}
            lastRefreshed={lastRefreshed}
            onRefresh={() => loadPullRequests(selectedRepository)}
            onSelectPR={handleSelectPR}
            onSwitchRepository={() => setConnectModalOpen(true)}
            isDevMode={isDevMode}
          />
        )}

        {/* View 2: PR Details & Inspection */}
        {currentView === 'pr_detail' && selectedRepository && selectedPR && (
          <PullRequestDetails
            repository={selectedRepository}
            pr={selectedPR}
            analysisRecord={currentAnalysisMap[selectedPR.number]}
            isSubmitting={isSubmittingAnalysis}
            onBackToInbox={() => setCurrentView('inbox')}
            onStartAnalysis={() => handleStartAnalysis()}
            onReopenAnalysis={handleReopenAnalysis}
          />
        )}

        {/* View 3: Manual Investigation Option */}
        {currentView === 'manual' && (
          <ManualInvestigation
            currentRepository={selectedRepository}
            isSubmitting={isSubmittingAnalysis}
            onSubmit={(req) => handleStartAnalysis(req)}
          />
        )}

        {/* View 4: Investigation History */}
        {currentView === 'history' && (
          <InvestigationHistory
            investigations={getInvestigationHistory(selectedRepository?.id)}
            onOpenReport={handleReopenAnalysis}
          />
        )}

        {/* View 5: Live Investigation Workspace */}
        {currentView === 'investigation' && currentAnalysis && (
          <div className="investigation-workspace">
            {/* Top Back and Export Bar */}
            <div className="workspace-top-bar">
              <button
                type="button"
                className="btn-back"
                onClick={() => {
                  if (selectedPR) {
                    setCurrentView('pr_detail');
                  } else {
                    setCurrentView('inbox');
                  }
                }}
              >
                <IconArrowLeft size={14} />
                <span>{selectedPR ? `Back to PR #${selectedPR.number}` : 'Back to Inbox'}</span>
              </button>

              <div className="workspace-export-actions">
                <a
                  href={getExportUrl(currentAnalysis.id, 'json')}
                  download={`nobluff-${currentAnalysis.id}.json`}
                  className="btn btn-secondary btn-sm"
                  title="Download backend report as JSON"
                >
                  <IconDownload size={13} />
                  <span>Export JSON</span>
                </a>
                <a
                  href={getExportUrl(currentAnalysis.id, 'markdown')}
                  download={`nobluff-${currentAnalysis.id}.md`}
                  className="btn btn-secondary btn-sm"
                  title="Download backend report as Markdown"
                >
                  <IconFileCode size={13} />
                  <span>Export Markdown</span>
                </a>
              </div>
            </div>

            {/* Stage Progress (when running or encountering errors) */}
            {(currentAnalysis.stage !== 'complete' || isPolling) && (
              <InvestigationProgress
                stage={currentAnalysis.stage}
                analysisId={currentAnalysis.id}
                errors={currentAnalysis.errors}
                pollCount={pollCount}
                onStopWaiting={stopPolling}
                onRefreshNow={() => pollAnalysis(currentAnalysis.id)}
              />
            )}

            {/* Claims and Findings */}
            <ClaimsList
              claims={currentAnalysis.claims}
              findings={currentAnalysis.findings}
              evidence={currentAnalysis.evidence}
              onSelectEvidence={handleOpenEvidence}
            />

            {/* Same-Test Before & After Comparison */}
            {currentAnalysis.comparisons.length > 0 && (
              <ComparisonView
                comparisons={currentAnalysis.comparisons}
                executions={currentAnalysis.executions}
                originalRevision={currentAnalysis.revision}
                comparisonRevision={currentAnalysis.comparison_revision}
              />
            )}

            {/* Controlled Container Execution Results */}
            {currentAnalysis.executions.length > 0 && (
              <ExecutionResults
                executions={currentAnalysis.executions}
                approvedTests={currentAnalysis.approved_tests}
              />
            )}

            {/* Reproduction Test Approval Form */}
            {currentAnalysis.claims.length > 0 && (
              <ReproductionForm
                claims={currentAnalysis.claims}
                hasComparisonRevision={Boolean(currentAnalysis.comparison_revision)}
                originalRevision={currentAnalysis.revision}
                comparisonRevision={currentAnalysis.comparison_revision}
                isRunning={isPolling}
                verificationEnabled={health?.verification ?? false}
                onSubmitRun={handleSubmitReproduction}
              />
            )}
          </div>
        )}
      </main>

      {/* Contextual Evidence Drawer */}
      <EvidenceDrawer
        isOpen={drawerOpen}
        evidence={selectedEvidence}
        execution={
          selectedEvidence?.execution_id
            ? currentAnalysis?.executions.find(
                (e) => e.id === selectedEvidence.execution_id,
              )
            : null
        }
        repositoryUrl={selectedRepository?.url}
        onClose={() => setDrawerOpen(false)}
      />

      {/* Screen 1: Connect Repository Modal */}
      <ConnectRepositoryModal
        isOpen={connectModalOpen || isInitialSetup}
        isInitialSetup={isInitialSetup}
        onClose={() => setConnectModalOpen(false)}
        onConnected={handleConnectedNewRepo}
      />

      {/* Settings & Status Modal */}
      <SettingsModal
        isOpen={settingsModalOpen}
        connectedRepositories={connectedRepos}
        selectedRepoId={selectedRepoId}
        health={health}
        healthLoading={healthLoading}
        isDevMode={isDevMode}
        onClose={() => setSettingsModalOpen(false)}
        onRefreshHealth={checkHealth}
        onSelectRepo={handleSelectRepo}
        onDisconnectRepo={handleDisconnectRepo}
        onToggleDevMode={handleToggleDevMode}
        onConnectNewRepo={() => {
          setSettingsModalOpen(false);
          setConnectModalOpen(true);
        }}
      />
    </div>
  );
}
