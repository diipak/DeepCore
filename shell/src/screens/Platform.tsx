import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import type { 
  WorkspaceDiagnostics, SyncRun, PlatformHealth, SubsystemHealth, Workspace,
  SystemObservabilityResponse, ConnectorInfo, SyncStatus
} from '../services/api';
import { 
  Database, CheckCircle, 
  Settings, Server, Heart, AlertTriangle, 
  XCircle, GitBranch, Layout, Shield, History,
  Eye, Cpu, Terminal, Activity, Plus, ShieldCheck
} from 'lucide-react';

import { DiscoveryStage } from '../components/connectors/DiscoveryStage';
import { UnderstandingStage } from '../components/connectors/UnderstandingStage';
import { ConfigurationStage } from '../components/connectors/ConfigurationStage';
import { AuthorizationStage } from '../components/connectors/AuthorizationStage';
import { PreviewStage } from '../components/connectors/PreviewStage';
import { IngestionStage } from '../components/connectors/IngestionStage';
import { VerificationStage } from '../components/connectors/VerificationStage';
import { TrustStage } from '../components/connectors/TrustStage';

type OnboardingState = 
  | 'discovery'
  | 'understanding'
  | 'configuration'
  | 'authorization'
  | 'preview'
  | 'ingestion'
  | 'verification'
  | 'trust';

export const Platform: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'health' | 'workspaces' | 'sources' | 'history' | 'pipeline' | 'diagnostics' | 'observability'>('health');
  
  // API State
  const [diagnostics, setDiagnostics] = useState<WorkspaceDiagnostics | null>(null);
  const [health, setHealth] = useState<PlatformHealth | null>(null);
  const [runs, setRuns] = useState<SyncRun[]>([]);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [observability, setObservability] = useState<SystemObservabilityResponse | null>(null);
  const [connectors, setConnectors] = useState<ConnectorInfo[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  
  // Onboarding wizard states
  const [onboardingState, setOnboardingState] = useState<OnboardingState | null>(null);
  const [selectedProvider, setSelectedProvider] = useState<string>('markdown');
  const [targetLocation, setTargetLocation] = useState<string>('');
  const [ingestionStatus, setIngestionStatus] = useState<SyncStatus | null>(null);
  const [selectedConnector, setSelectedConnector] = useState<ConnectorInfo | null>(null);

  // Form state for workspace creation
  const [newWorkspaceName, setNewWorkspaceName] = useState<string>('');
  
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const loadAllData = async () => {
    try {
      const [diagData, healthData, runsData, wsData, connectorList] = await Promise.all([
        api.getWorkspaceDiagnostics(),
        api.getPlatformHealth(),
        api.getSyncRuns(),
        api.listWorkspaces(),
        api.getConnectors()
      ]);
      setDiagnostics(diagData);
      setHealth(healthData);
      setRuns(runsData);
      setWorkspaces(wsData);
      setConnectors(connectorList);
      setErrorMsg(null);

      // Fault Isolation: Fetch observability separately so it does not block the Platform dashboard
      try {
        const obsData = await api.getObservability();
        setObservability(obsData);
      } catch (obsErr: any) {
        console.error('Failed to retrieve observability data', obsErr);
      }
    } catch (err: any) {
      console.error('Failed to load platform data', err);
      setErrorMsg(err.message || 'Failed to retrieve platform state.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAllData();
  }, []);





  const handleCreateWorkspace = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newWorkspaceName.trim()) return;
    setErrorMsg(null);
    setSuccessMsg(null);
    try {
      const newWs = await api.createWorkspace(newWorkspaceName);
      setNewWorkspaceName('');
      setSuccessMsg(`Workspace "${newWs.name}" created successfully.`);
      localStorage.setItem('activeWorkspaceUuid', newWs.uuid);
      window.location.reload();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to create workspace.');
    }
  };

  const switchWorkspace = (uuid: string) => {
    localStorage.setItem('activeWorkspaceUuid', uuid);
    window.location.reload();
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center animate-pulse">
        <Server className="w-12 h-12 text-accent-primary animate-bounce mb-4" />
        <p className="text-sm text-text-secondary">Resolving control runtime state...</p>
      </div>
    );
  }

  // Format subsystem health status badge
  const renderHealthBadge = (status: string) => {
    switch (status) {
      case 'healthy':
        return (
          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-green-500/10 text-green-400 border border-green-500/20 flex items-center space-x-1">
            <CheckCircle className="w-3 h-3 shrink-0" />
            <span>Healthy</span>
          </span>
        );
      case 'degraded':
        return (
          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-yellow-500/10 text-yellow-400 border border-yellow-500/20 flex items-center space-x-1">
            <AlertTriangle className="w-3 h-3 shrink-0" />
            <span>Degraded</span>
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-red-500/10 text-red-400 border border-red-500/20 flex items-center space-x-1">
            <XCircle className="w-3 h-3 shrink-0" />
            <span>Unhealthy</span>
          </span>
        );
    }
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto w-full select-text pb-12 animate-fade-in">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border-primary/60 pb-6">
        <div>
          <h2 className="font-extrabold text-2xl tracking-tight text-text-primary flex items-center space-x-2">
            <Shield className="w-7 h-7 text-accent-primary shrink-0" />
            <span>Platform Dashboard</span>
          </h2>
          <p className="text-xs text-text-secondary mt-1">
            Active Workspace: <strong className="text-text-primary">{diagnostics?.workspace_name}</strong> &bull; UUID: <code className="text-[10px]">{diagnostics?.workspace_uuid}</code>
          </p>
        </div>
        
        {/* Quick Sync Status */}
        {diagnostics?.last_sync_run && (
          <div className="text-right text-[10px] text-text-secondary bg-surface-card border border-border-primary/60 rounded-xl px-4 py-2.5 max-w-xs shrink-0 shadow-sm">
            <span className="font-bold block uppercase tracking-wider text-text-primary/75">Last Sync Audit</span>
            <span className="mt-0.5 block truncate">
              {diagnostics.last_sync_run.provider} &bull; {diagnostics.last_sync_run.status === 'success' ? '🟢 Success' : '🔴 Failed'}
            </span>
          </div>
        )}
      </div>

      {/* Messages */}
      {errorMsg && (
        <div className="flex items-center space-x-2 text-xs text-red-500 bg-red-500/10 p-3 rounded-xl border border-red-500/20">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}
      {successMsg && (
        <div className="flex items-center space-x-2 text-xs text-green-500 bg-green-500/10 p-3 rounded-xl border border-green-500/20">
          <CheckCircle className="w-4 h-4 shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      {/* Tabs list */}
      <div className="flex border-b border-border-primary/60 overflow-x-auto space-x-1 py-1">
        {[
          { id: 'health', label: 'Platform Health', icon: Heart },
          { id: 'workspaces', label: 'Workspaces', icon: Layout },
          { id: 'sources', label: 'Knowledge Sources', icon: Database },
          { id: 'history', label: 'Runs History', icon: History },
          { id: 'pipeline', label: 'Processing Pipeline', icon: GitBranch },
          { id: 'observability', label: 'Developer Observability', icon: Eye },
          { id: 'diagnostics', label: 'System Info', icon: Settings },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center space-x-2 px-4 py-2.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-all cursor-pointer border ${
                isActive 
                  ? 'bg-accent-primary/10 text-accent-primary border-accent-primary/20 font-bold'
                  : 'text-text-secondary hover:bg-background-primary hover:text-text-primary border-transparent'
              }`}
            >
              <Icon className="w-4 h-4 shrink-0" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Tab Content Panels */}
      <div className="mt-4">
        
        {/* 1. HEALTH TAB */}
        {activeTab === 'health' && health && (
          <div className="space-y-6">
            <div className="p-4 rounded-xl border border-border-primary bg-surface-card flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <span className="text-xl">🏥</span>
                <div>
                  <h4 className="text-sm font-bold text-text-primary">Overall Platform Status</h4>
                  <p className="text-xs text-text-secondary">Summary of all registered core subsystems</p>
                </div>
              </div>
              {renderHealthBadge(health.status)}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {Object.entries(health.subsystems).map(([key, sub]: [string, SubsystemHealth]) => {
                const title = key.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
                return (
                  <div key={key} className="p-4 rounded-xl border border-border-primary bg-surface-card space-y-2 flex flex-col justify-between shadow-xs">
                    <div className="space-y-1">
                      <div className="flex items-center justify-between">
                        <h5 className="text-xs font-bold text-text-primary tracking-tight">{title}</h5>
                        {renderHealthBadge(sub.status)}
                      </div>
                      <p className="text-xs text-text-secondary font-medium mt-1 leading-relaxed">
                        {sub.message || 'Status OK'}
                      </p>
                    </div>

                    {/* Extensible Metrics rendering */}
                    {sub.metrics && Object.keys(sub.metrics).length > 0 && (
                      <div className="pt-2 border-t border-border-primary/40 mt-2">
                        <details className="cursor-pointer group">
                          <summary className="text-[9px] font-bold text-text-secondary uppercase tracking-widest list-none flex items-center justify-between hover:text-text-primary transition-colors">
                            <span>Diagnostics Metrics</span>
                            <span className="transition-transform group-open:rotate-180">▼</span>
                          </summary>
                          <pre className="mt-1.5 p-2 rounded bg-background-primary border border-border-primary/60 text-[9px] font-mono text-text-secondary overflow-x-auto select-all max-h-32">
                            {JSON.stringify(sub.metrics, null, 2)}
                          </pre>
                        </details>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* 2. WORKSPACES TAB */}
        {activeTab === 'workspaces' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 space-y-4">
              <h4 className="text-sm font-bold text-text-primary px-1">Registered Workspaces</h4>
              <div className="space-y-3">
                {workspaces.map((ws) => {
                  const isActive = ws.uuid === diagnostics?.workspace_uuid;
                  return (
                    <div 
                      key={ws.uuid} 
                      className={`p-4 rounded-xl border transition-all flex items-center justify-between bg-surface-card ${
                        isActive ? 'border-accent-primary shadow-sm shadow-accent-primary/5' : 'border-border-primary'
                      }`}
                    >
                      <div className="space-y-1">
                        <span className="text-sm font-bold text-text-primary flex items-center space-x-1.5">
                          <span>{ws.name}</span>
                          {isActive && <span className="text-[9px] font-bold bg-accent-primary/10 text-accent-primary border border-accent-primary/15 px-1.5 py-0.5 rounded-md">Active</span>}
                        </span>
                        <span className="text-[10px] text-text-secondary font-mono block">UUID: {ws.uuid}</span>
                      </div>
                      
                      {!isActive && (
                        <button
                          onClick={() => switchWorkspace(ws.uuid)}
                          className="px-3 py-1.5 bg-background-primary text-text-primary rounded-lg text-xs font-semibold hover:bg-background-primary/80 border border-border-primary transition-all cursor-pointer"
                        >
                          Switch to Workspace
                        </button>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Create Workspace Panel */}
            <div className="p-5 rounded-xl border border-border-primary bg-surface-card shadow-sm space-y-4 self-start">
              <h4 className="text-sm font-bold text-text-primary">Create Workspace</h4>
              <p className="text-xs text-text-secondary">Set up a completely separate and isolated knowledge database workspace.</p>
              <form onSubmit={handleCreateWorkspace} className="space-y-3">
                <input
                  type="text"
                  value={newWorkspaceName}
                  onChange={(e) => setNewWorkspaceName(e.target.value)}
                  className="w-full bg-background-primary border border-border-primary rounded-lg px-3 py-2 text-xs text-text-primary focus:outline-none focus:ring-1 focus:ring-accent-primary font-medium"
                  placeholder="e.g. Finance Vault"
                />
                <button
                  type="submit"
                  disabled={!newWorkspaceName.trim()}
                  className="w-full py-2 bg-accent-primary text-white rounded-lg font-bold hover:bg-accent-primary/95 text-xs transition-all disabled:opacity-60 cursor-pointer"
                >
                  Create Workspace
                </button>
              </form>
            </div>
          </div>
        )}

        {/* 3. SOURCES TAB */}
        {activeTab === 'sources' && (
          <div className="space-y-6">
            {selectedConnector ? (
              <TrustStage
                connector={selectedConnector}
                onBack={() => {
                  setSelectedConnector(null);
                  loadAllData();
                }}
                onRefresh={loadAllData}
              />
            ) : onboardingState ? (
              <div className="space-y-4 max-w-xl mx-auto text-left">
                {/* Onboarding State Header / Indicator */}
                <div className="flex items-center justify-between p-3.5 rounded-xl border border-border-primary bg-surface-card text-xs">
                  <div className="flex items-center space-x-2 font-bold text-text-primary">
                    <ShieldCheck className="w-4 h-4 text-accent-primary" />
                    <span className="capitalize">Onboarding: {onboardingState}</span>
                  </div>
                  <button
                    onClick={() => {
                      setOnboardingState(null);
                      loadAllData();
                    }}
                    className="text-[10px] font-bold text-accent-important hover:underline cursor-pointer"
                  >
                    Abort Journey
                  </button>
                </div>

                {onboardingState === 'discovery' && (
                  <DiscoveryStage
                    onSelect={(prov) => {
                      setSelectedProvider(prov);
                      setOnboardingState('understanding');
                    }}
                  />
                )}

                {onboardingState === 'understanding' && (
                  <UnderstandingStage
                    onNext={() => setOnboardingState('configuration')}
                    onBack={() => setOnboardingState('discovery')}
                  />
                )}

                {onboardingState === 'configuration' && (
                  <ConfigurationStage
                    onNext={(loc) => {
                      setTargetLocation(loc);
                      setOnboardingState('authorization');
                    }}
                    onBack={() => setOnboardingState('understanding')}
                  />
                )}

                {onboardingState === 'authorization' && (
                  <AuthorizationStage
                    location={targetLocation}
                    providerId={selectedProvider}
                    onNext={() => setOnboardingState('preview')}
                    onBack={() => setOnboardingState('configuration')}
                  />
                )}

                {onboardingState === 'preview' && (
                  <PreviewStage
                    location={targetLocation}
                    providerId={selectedProvider}
                    onNext={() => setOnboardingState('ingestion')}
                    onBack={() => setOnboardingState('configuration')}
                  />
                )}

                {onboardingState === 'ingestion' && (
                  <IngestionStage
                    location={targetLocation}
                    providerId={selectedProvider}
                    onNext={(syncStatus) => {
                      setIngestionStatus(syncStatus);
                      setOnboardingState('verification');
                    }}
                    onCancel={() => setOnboardingState('configuration')}
                  />
                )}

                {onboardingState === 'verification' && (
                  <VerificationStage
                    status={ingestionStatus}
                    onNext={() => {
                      setOnboardingState(null);
                      loadAllData();
                    }}
                  />
                )}
              </div>
            ) : (
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Active Sources List */}
                <div className="lg:col-span-2 space-y-4">
                  <div className="flex items-center justify-between px-1">
                    <h4 className="text-sm font-bold text-text-primary">Trusted Connectors</h4>
                    <button
                      onClick={() => setOnboardingState('discovery')}
                      className="flex items-center space-x-1.5 px-3 py-1.5 bg-accent-primary text-white rounded-xl text-xs font-bold shadow-md shadow-accent-primary/10 hover:bg-accent-primary/95 transition-all cursor-pointer"
                    >
                      <Plus className="w-3.5 h-3.5" />
                      <span>Connect Source</span>
                    </button>
                  </div>
                  
                  <div className="space-y-3">
                    {connectors && connectors.length > 0 ? (
                      connectors.map((conn) => (
                        <div
                          key={conn.uuid}
                          onClick={() => setSelectedConnector(conn)}
                          className="p-4 rounded-xl border border-border-primary bg-surface-card flex items-center justify-between gap-4 shadow-xs hover:border-accent-primary transition-all cursor-pointer text-left"
                        >
                          <div className="min-w-0 space-y-1">
                            <span className="text-sm font-bold text-text-primary block">{conn.name}</span>
                            <span className="text-[10px] text-text-secondary font-mono block truncate">
                              {conn.provider_id.toUpperCase()} &bull; {conn.kind} &bull; Location: {conn.location}
                            </span>
                          </div>
                          
                          <div className="flex items-center space-x-3 shrink-0">
                            <span className={`px-2 py-0.5 rounded-full text-[9px] font-bold ${
                              conn.status === 'Configured' || conn.status === 'HEALTHY' || conn.status === 'active'
                                ? 'bg-green-500/10 text-green-400 border border-green-500/20'
                                : 'bg-red-500/10 text-red-400 border border-red-500/20'
                            }`}>
                              {conn.status.toUpperCase()}
                            </span>
                            <span className="text-[10px] text-text-secondary hover:text-text-primary font-bold">
                              Manage &rarr;
                            </span>
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="p-8 rounded-xl border border-dashed border-border-primary text-center">
                        <p className="text-xs text-text-secondary font-medium">No knowledge sources registered in this workspace yet.</p>
                      </div>
                    )}
                  </div>
                </div>

                {/* Info summary */}
                <div className="p-5 rounded-xl border border-border-primary bg-surface-card shadow-sm space-y-4 self-start text-left">
                  <h4 className="text-sm font-bold text-text-primary">Source Connectors</h4>
                  <p className="text-xs text-text-secondary leading-relaxed">
                    Connectors act as secure, isolated pipelines. DeepCore monitors directories, index files locally, and tracks modification events deterministically.
                  </p>
                  <p className="text-xs text-text-secondary leading-relaxed">
                    Click <strong>Connect Source</strong> to walk through the 8-stage Trust lifecycle.
                  </p>
                </div>
              </div>
            )}
          </div>
        )}

        {/* 4. RUNS HISTORY TAB */}
        {activeTab === 'history' && (
          <div className="space-y-4">
            <h4 className="text-sm font-bold text-text-primary px-1">Runs History Scoped to Workspace</h4>
            <div className="overflow-x-auto border border-border-primary rounded-xl bg-surface-card">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b border-border-primary bg-background-primary/40 text-text-secondary uppercase tracking-wider font-bold">
                    <th className="p-3">Run Date</th>
                    <th className="p-3">Provider</th>
                    <th className="p-3">Location</th>
                    <th className="p-3">Status</th>
                    <th className="p-3 text-center">Scanned</th>
                    <th className="p-3 text-center">New</th>
                    <th className="p-3 text-center flex items-center justify-center space-x-1"><span>Errors</span></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-primary/20 text-text-primary">
                  {runs.length > 0 ? (
                    runs.map((run) => (
                      <tr key={run.uuid} className="hover:bg-background-primary/20 transition-colors">
                        <td className="p-3 font-semibold whitespace-nowrap">
                          {new Date(run.started_at).toLocaleString()}
                        </td>
                        <td className="p-3 font-mono">{run.provider}</td>
                        <td className="p-3 font-mono max-w-xs truncate" title={run.source_location}>
                          {run.source_location}
                        </td>
                        <td className="p-3">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            run.status === 'success'
                              ? 'bg-green-500/10 text-green-400 border border-green-500/15'
                              : 'bg-red-500/10 text-red-400 border border-red-500/15'
                          }`}>
                            {run.status.toUpperCase()}
                          </span>
                        </td>
                        <td className="p-3 text-center font-mono">{run.objects_scanned}</td>
                        <td className="p-3 text-center font-mono text-green-500">+{run.objects_created}</td>
                        <td className="p-3 text-text-secondary max-w-xs truncate" title={run.errors_json || 'None'}>
                          {run.errors_json ? (
                            <span className="text-red-400 font-mono text-[10px]">{run.errors_json}</span>
                          ) : (
                            <span className="text-text-secondary/40 italic">None</span>
                          )}
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={7} className="p-8 text-center text-text-secondary italic">
                        No runs recorded in this workspace.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* 5. PIPELINE & STAGES TAB */}
        {activeTab === 'pipeline' && (
          <div className="space-y-4">
            <h4 className="text-sm font-bold text-text-primary px-1">Processing Pipeline Configuration</h4>
            <div className="space-y-3">
              {diagnostics?.active_stages && diagnostics.active_stages.map((stage, idx) => (
                <div key={stage.id} className="p-4 rounded-xl border border-border-primary bg-surface-card flex items-center justify-between shadow-xs">
                  <div className="flex items-center space-x-4">
                    <div className="w-8 h-8 rounded-lg bg-background-primary flex items-center justify-center font-bold text-xs border border-border-primary">
                      {idx + 1}
                    </div>
                    <div>
                      <span className="text-sm font-bold text-text-primary block">{stage.name}</span>
                      <span className="text-[10px] text-text-secondary font-mono block">
                        Stage ID: {stage.id} &bull; Order Index: {stage.order}
                      </span>
                    </div>
                  </div>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                    stage.enabled
                      ? 'bg-green-500/10 text-green-400 border border-green-500/15'
                      : 'bg-background-primary text-text-secondary/50 border border-border-primary'
                  }`}>
                    {stage.enabled ? 'Enabled' : 'Disabled'}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 6. DIAGNOSTICS & SYSTEM INFO TAB */}
        {activeTab === 'diagnostics' && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            
            {/* System Info */}
            <div className="p-5 rounded-xl border border-border-primary bg-surface-card shadow-sm space-y-4">
              <h4 className="text-sm font-bold text-text-primary">System Information</h4>
              <div className="space-y-3 text-xs">
                <div className="flex justify-between py-1 border-b border-border-primary/30">
                  <span className="text-text-secondary">Database Path</span>
                  <span className="font-mono text-text-primary break-all max-w-[200px] text-right">{diagnostics?.db_path}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-border-primary/30">
                  <span className="text-text-secondary">DeepCore Version</span>
                  <span className="font-mono text-text-primary">0.1.0 (Hardened)</span>
                </div>
                <div className="flex justify-between py-1 border-b border-border-primary/30">
                  <span className="text-text-secondary">Server Local Time</span>
                  <span className="font-mono text-text-primary">{new Date().toLocaleString()}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-border-primary/30">
                  <span className="text-text-secondary">Active Providers</span>
                  <span className="font-mono text-text-primary capitalize">{diagnostics?.registered_providers?.join(', ')}</span>
                </div>
              </div>
            </div>

            {/* Counts */}
            <div className="p-5 rounded-xl border border-border-primary bg-surface-card shadow-sm space-y-4">
              <h4 className="text-sm font-bold text-text-primary">Workspace Statistics</h4>
              <div className="space-y-3 text-xs">
                <div className="flex justify-between py-1 border-b border-border-primary/30">
                  <span className="text-text-secondary">Registry Objects</span>
                  <span className="font-mono font-bold text-text-primary">{diagnostics?.object_count}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-border-primary/30">
                  <span className="text-text-secondary">Relationships</span>
                  <span className="font-mono font-bold text-text-primary">{diagnostics?.relationship_count}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-border-primary/30">
                  <span className="text-text-secondary">Temporal Signals</span>
                  <span className="font-mono font-bold text-text-primary">{diagnostics?.signal_count}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-border-primary/30">
                  <span className="text-text-secondary">Knowledge Sources</span>
                  <span className="font-mono font-bold text-text-primary">{diagnostics?.registered_sources?.length || 0}</span>
                </div>
              </div>
            </div>
            
          </div>
        )}

        {/* 7. DEVELOPER OBSERVABILITY TAB */}
        {activeTab === 'observability' && observability && (
          <div className="space-y-6">
            
            {/* Dynamic Ingestion Timeline */}
            <div className="p-5 rounded-xl border border-border-primary bg-surface-card shadow-sm space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="text-sm font-bold text-text-primary flex items-center space-x-1.5">
                    <Activity className="w-4 h-4 text-accent-primary animate-pulse" />
                    <span>Pipeline Progression Timeline</span>
                  </h4>
                  <p className="text-[10px] text-text-secondary mt-0.5">
                    Real-time execution phases from source import to signal engine assembly
                  </p>
                </div>
                {observability.timeline && (
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                    observability.timeline.status === 'success'
                      ? 'bg-green-500/10 text-green-400 border border-green-500/15'
                      : 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/15'
                  }`}>
                    RUN STATUS: {observability.timeline.status.toUpperCase()}
                  </span>
                )}
              </div>

              {observability.timeline?.stages && observability.timeline.stages.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-7 gap-3 pt-2">
                  {observability.timeline.stages.map((stage, idx) => {
                    const isSuccess = stage.status === 'completed' || stage.status === 'success';
                    const isRunning = stage.status === 'running';
                    const isFailed = stage.status === 'failed';
                    
                    return (
                      <div key={stage.id} className={`p-3 rounded-lg border flex flex-col justify-between h-28 relative ${
                        isRunning 
                          ? 'border-accent-primary bg-accent-primary/5 animate-pulse'
                          : isFailed
                          ? 'border-red-500/30 bg-red-500/5'
                          : isSuccess
                          ? 'border-green-500/15 bg-green-500/[0.01]'
                          : 'border-border-primary/50 bg-background-primary/20'
                      }`}>
                        <div>
                          <div className="flex items-center justify-between">
                            <span className="text-[9px] text-text-secondary/70 font-bold uppercase tracking-wider">
                              Phase 0{idx + 1}
                            </span>
                            <span className={`w-2 h-2 rounded-full ${
                              isRunning
                                ? 'bg-accent-primary'
                                : isFailed
                                ? 'bg-red-500'
                                : isSuccess
                                ? 'bg-green-500'
                                : 'bg-text-secondary/30'
                            }`} />
                          </div>
                          <span className="text-[11px] font-bold text-text-primary block mt-1.5 leading-tight">
                            {stage.name}
                          </span>
                        </div>

                        <div className="mt-2 flex items-center justify-between border-t border-border-primary/20 pt-1.5">
                          <span className="text-[10px] font-mono text-text-secondary">
                            {stage.duration_ms > 0 ? `${stage.duration_ms.toFixed(0)}ms` : '—'}
                          </span>
                          <span className="text-[9px] font-semibold text-text-secondary uppercase">
                            {stage.status}
                          </span>
                        </div>

                        {/* Error details inside tooltip or undercard if failed */}
                        {stage.errors.length > 0 && (
                          <div className="absolute -bottom-10 left-0 right-0 z-10 p-1.5 bg-red-950/90 border border-red-500/30 rounded text-[9px] text-red-400 font-mono">
                            {stage.errors[0]}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="p-8 text-center text-xs text-text-secondary italic border border-dashed border-border-primary rounded-lg">
                  No execution timeline data available for the active workspace. Trigger a source sync to run the pipeline.
                </div>
              )}
            </div>

            {/* In-Process Runtimes & Registries Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              
              {/* Registered Runtimes */}
              <div className="lg:col-span-2 p-5 rounded-xl border border-border-primary bg-surface-card shadow-sm space-y-4">
                <h4 className="text-sm font-bold text-text-primary flex items-center space-x-1.5">
                  <Cpu className="w-4 h-4 text-accent-primary" />
                  <span>Registered Runtime Components</span>
                </h4>
                
                <div className="overflow-x-auto border border-border-primary rounded-lg">
                  <table className="w-full text-left border-collapse text-[11px]">
                    <thead>
                      <tr className="border-b border-border-primary bg-background-primary/40 text-text-secondary uppercase tracking-wider font-bold">
                        <th className="p-2.5">Runtime</th>
                        <th className="p-2.5">Version</th>
                        <th className="p-2.5">Dependencies</th>
                        <th className="p-2.5">Capabilities</th>
                        <th className="p-2.5 text-right">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border-primary/20 text-text-primary font-medium">
                      {observability.registered_runtimes.map((rt) => (
                        <tr key={rt.name} className="hover:bg-background-primary/10 transition-colors">
                          <td className="p-2.5 font-bold">{rt.name}</td>
                          <td className="p-2.5 font-mono text-text-secondary">{rt.version}</td>
                          <td className="p-2.5 font-mono text-text-secondary max-w-[120px] truncate" title={rt.dependencies.join(', ')}>
                            {rt.dependencies.join(', ') || 'None'}
                          </td>
                          <td className="p-2.5">
                            <div className="flex flex-wrap gap-1">
                              {rt.capabilities.slice(0, 3).map(cap => (
                                <span key={cap} className="px-1.5 py-0.5 rounded bg-background-primary border border-border-primary text-[9px] font-mono">
                                  {cap}
                                </span>
                              ))}
                              {rt.capabilities.length > 3 && (
                                <span className="text-[9px] text-text-secondary/70">+{rt.capabilities.length - 3} more</span>
                              )}
                            </div>
                          </td>
                          <td className="p-2.5 text-right">
                            <span className="px-2 py-0.5 rounded bg-green-500/10 text-green-400 font-bold border border-green-500/15 uppercase text-[9px]">
                              {rt.health}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Capability Descriptor Registry */}
              <div className="p-5 rounded-xl border border-border-primary bg-surface-card shadow-sm space-y-4">
                <h4 className="text-sm font-bold text-text-primary flex items-center space-x-1.5">
                  <Terminal className="w-4 h-4 text-accent-primary" />
                  <span>Descriptor Registry</span>
                </h4>

                <div className="space-y-2 max-h-[220px] overflow-y-auto pr-1">
                  {observability.descriptor_registry.map((desc) => (
                    <div key={desc.id} className="p-2.5 rounded-lg border border-border-primary bg-background-primary/20 flex flex-col justify-between space-y-1">
                      <div className="flex justify-between items-start">
                        <span className="font-bold text-[11px] text-text-primary">{desc.name}</span>
                        <span className="text-[9px] font-bold font-mono px-1.5 py-0.5 rounded bg-accent-primary/10 text-accent-primary">
                          {desc.category.toUpperCase()}
                        </span>
                      </div>
                      <div className="flex justify-between items-center text-[10px] text-text-secondary">
                        <span className="font-mono">ID: {desc.id}</span>
                        <span>v{desc.version}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

            </div>

            {/* Execution History & Execution queue */}
            <div className="p-5 rounded-xl border border-border-primary bg-surface-card shadow-sm space-y-4">
              <h4 className="text-sm font-bold text-text-primary">Execution Logs & Queue</h4>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                
                {/* Ingestion Queue */}
                <div className="p-4 rounded-xl border border-border-primary/50 bg-background-primary/20 space-y-3">
                  <span className="text-[10px] font-bold text-text-secondary uppercase tracking-wider block">Execution Queue</span>
                  {observability.execution_queue.length > 0 ? (
                    observability.execution_queue.map(q => (
                      <div key={q.uuid} className="p-3 bg-surface-card border border-border-primary rounded-lg flex items-center justify-between">
                        <div>
                          <span className="text-xs font-bold text-text-primary block">{q.provider}</span>
                          <span className="text-[10px] font-mono text-text-secondary block truncate max-w-[150px]">{q.source_location}</span>
                        </div>
                        <span className="w-2.5 h-2.5 rounded-full bg-accent-primary animate-ping" />
                      </div>
                    ))
                  ) : (
                    <span className="text-xs text-text-secondary/60 italic block py-2">Queue is empty (Platform idle)</span>
                  )}
                </div>

                {/* Performance stats */}
                <div className="md:col-span-2 p-4 rounded-xl border border-border-primary/50 bg-background-primary/20 space-y-3">
                  <span className="text-[10px] font-bold text-text-secondary uppercase tracking-wider block">Last Successful Execution Duration</span>
                  {observability.execution_history.length > 0 ? (
                    <div className="grid grid-cols-3 gap-4 text-center">
                      <div className="p-3 bg-surface-card border border-border-primary rounded-lg">
                        <span className="text-[10px] text-text-secondary uppercase tracking-wider block">Total Run</span>
                        <span className="text-lg font-bold font-mono text-text-primary">
                          {observability.execution_history[0].completed_at && observability.execution_history[0].started_at
                            ? `${((new Date(observability.execution_history[0].completed_at).getTime() - new Date(observability.execution_history[0].started_at).getTime()) / 1000).toFixed(2)}s`
                            : 'N/A'
                          }
                        </span>
                      </div>
                      <div className="p-3 bg-surface-card border border-border-primary rounded-lg">
                        <span className="text-[10px] text-text-secondary uppercase tracking-wider block">Scanned Files</span>
                        <span className="text-lg font-bold font-mono text-text-primary">
                          {observability.execution_history[0].objects_scanned}
                        </span>
                      </div>
                      <div className="p-3 bg-surface-card border border-border-primary rounded-lg">
                        <span className="text-[10px] text-text-secondary uppercase tracking-wider block">New Imports</span>
                        <span className="text-lg font-bold font-mono text-green-400">
                          +{observability.execution_history[0].objects_created}
                        </span>
                      </div>
                    </div>
                  ) : (
                    <span className="text-xs text-text-secondary/60 italic block py-2">No run history metrics available</span>
                  )}
                </div>

              </div>
            </div>

          </div>
        )}

      </div>
    </div>
  );
};
