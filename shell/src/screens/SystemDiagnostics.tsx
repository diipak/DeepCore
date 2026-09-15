import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import type { WorkspaceDiagnostics } from '../services/api';
import { 
  Database, RefreshCw, Info, CheckCircle, Play, 
  Settings, Server, Activity, Plus 
} from 'lucide-react';

export const SystemDiagnostics: React.FC = () => {
  const [diagnostics, setDiagnostics] = useState<WorkspaceDiagnostics | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [syncingSourceUuid, setSyncingSourceUuid] = useState<string | null>(null);
  
  // Form state for adding new source
  const [newSourceName, setNewSourceName] = useState<string>('');
  const [newSourceLocation, setNewSourceLocation] = useState<string>('');
  const [newSourceKind, setNewSourceKind] = useState<string>('filesystem');
  const [newSourceProvider, setNewSourceProvider] = useState<string>('markdown');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const fetchDiagnostics = async () => {
    try {
      const data = await api.getWorkspaceDiagnostics();
      setDiagnostics(data);
      setErrorMsg(null);
    } catch (err: any) {
      console.error('Failed to fetch diagnostics', err);
      setErrorMsg(err.message || 'Failed to fetch diagnostics');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDiagnostics();
  }, []);

  const handleSyncSource = async (uuid: string) => {
    setSyncingSourceUuid(uuid);
    setSuccessMsg(null);
    setErrorMsg(null);
    try {
      const run = await api.syncSource(uuid);
      setSuccessMsg(`Synchronization completed: ${run.objects_created} created, ${run.objects_updated} updated, ${run.objects_missing} missing.`);
      await fetchDiagnostics();
    } catch (err: any) {
      console.error('Sync failed', err);
      setErrorMsg(err.message || 'Synchronization failed.');
    } finally {
      setSyncingSourceUuid(null);
    }
  };

  const handleAddSource = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newSourceName || !newSourceLocation) {
      setErrorMsg('Please fill in all fields.');
      return;
    }
    setErrorMsg(null);
    setSuccessMsg(null);
    
    const activeUuid = localStorage.getItem('activeWorkspaceUuid');
    if (!activeUuid) {
      setErrorMsg('No active workspace selected.');
      return;
    }

    try {
      await api.createWorkspaceSource(activeUuid, {
        name: newSourceName,
        kind: newSourceKind,
        provider_id: newSourceProvider,
        location: newSourceLocation,
      });
      setNewSourceName('');
      setNewSourceLocation('');
      setSuccessMsg('KnowledgeSource added successfully!');
      await fetchDiagnostics();
    } catch (err: any) {
      console.error('Failed to add source', err);
      setErrorMsg(err.message || 'Failed to add source');
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center animate-pulse">
        <Server className="w-12 h-12 text-accent-assistant animate-bounce" />
        <p className="text-sm text-text-secondary mt-4">Loading system diagnostics...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-4xl mx-auto w-full select-text pb-12 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="font-extrabold text-2xl tracking-tight text-text-primary">System Diagnostics</h2>
          <p className="text-sm text-text-secondary">Workspace isolation boundary & database overview</p>
        </div>
        <button 
          onClick={fetchDiagnostics}
          className="flex items-center space-x-2 bg-background-primary/40 hover:bg-background-primary transition-colors border border-border-primary rounded-lg px-3 py-1.5 text-xs font-semibold text-text-primary"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Refresh</span>
        </button>
      </div>

      {successMsg && (
        <div className="p-4 rounded-xl bg-accent-memory/10 border border-accent-memory/20 text-accent-memory text-xs flex items-start space-x-2">
          <CheckCircle className="w-4 h-4 shrink-0 mt-0.5" />
          <span>{successMsg}</span>
        </div>
      )}

      {errorMsg && (
        <div className="p-4 rounded-xl bg-accent-video/10 border border-accent-video/20 text-accent-video text-xs flex items-start space-x-2">
          <Info className="w-4 h-4 shrink-0 mt-0.5" />
          <span>{errorMsg}</span>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Workspace Card */}
        <div className="p-5 rounded-2xl border border-border-primary bg-surface-card space-y-4">
          <div className="flex items-center space-x-2">
            <Server className="w-4 h-4 text-accent-assistant" />
            <span className="font-bold text-sm text-text-primary">Active Workspace</span>
          </div>
          <div className="space-y-2">
            <div>
              <div className="text-[10px] uppercase font-bold text-text-secondary tracking-wider">Name</div>
              <div className="text-sm font-semibold text-text-primary">{diagnostics?.workspace_name}</div>
            </div>
            <div>
              <div className="text-[10px] uppercase font-bold text-text-secondary tracking-wider">UUID</div>
              <div className="text-xs font-mono text-text-secondary break-all">{diagnostics?.workspace_uuid}</div>
            </div>
          </div>
        </div>

        {/* Database Path Card */}
        <div className="p-5 rounded-2xl border border-border-primary bg-surface-card space-y-4 md:col-span-2">
          <div className="flex items-center space-x-2">
            <Database className="w-4 h-4 text-accent-assistant" />
            <span className="font-bold text-sm text-text-primary">SQLite Local Database</span>
          </div>
          <div className="space-y-2">
            <div>
              <div className="text-[10px] uppercase font-bold text-text-secondary tracking-wider">DB File Path</div>
              <div className="text-xs font-mono text-text-primary bg-background-primary/40 p-2 rounded-lg break-all border border-border-primary/20">
                {diagnostics?.db_path}
              </div>
            </div>
            <div className="grid grid-cols-3 gap-4 pt-1">
              <div>
                <div className="text-[10px] uppercase font-bold text-text-secondary tracking-wider">Objects</div>
                <div className="text-lg font-extrabold text-accent-memory">{diagnostics?.object_count}</div>
              </div>
              <div>
                <div className="text-[10px] uppercase font-bold text-text-secondary tracking-wider">Relations</div>
                <div className="text-lg font-extrabold text-accent-concept">{diagnostics?.relationship_count}</div>
              </div>
              <div>
                <div className="text-[10px] uppercase font-bold text-text-secondary tracking-wider">Signals</div>
                <div className="text-lg font-extrabold text-accent-assistant">{diagnostics?.signal_count}</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Ingestion Sources Section */}
      <div className="p-6 rounded-2xl border border-border-primary bg-surface-card space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Settings className="w-4 h-4 text-accent-assistant" />
            <span className="font-bold text-sm text-text-primary">Configured KnowledgeSources</span>
          </div>
        </div>

        {diagnostics?.registered_sources && diagnostics.registered_sources.length > 0 ? (
          <div className="space-y-4">
            {diagnostics.registered_sources.map((source) => {
              const isSyncing = syncingSourceUuid === source.uuid;
              return (
                <div key={source.uuid} className="p-4 rounded-xl bg-background-primary/20 border border-border-primary/50 flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div className="space-y-1">
                    <div className="flex items-center space-x-2">
                      <span className="font-bold text-xs text-text-primary">{source.name}</span>
                      <span className="text-[9px] uppercase font-bold px-1.5 py-0.5 rounded bg-background-primary text-text-secondary border border-border-primary/40">
                        {source.kind}
                      </span>
                      <span className="text-[9px] uppercase font-bold px-1.5 py-0.5 rounded bg-accent-memory/10 text-accent-memory">
                        {source.provider_id}
                      </span>
                    </div>
                    <div className="text-xs text-text-secondary font-mono truncate max-w-md">
                      Location: {source.location}
                    </div>
                  </div>
                  <button
                    onClick={() => handleSyncSource(source.uuid)}
                    disabled={isSyncing}
                    className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs font-bold transition-all shrink-0 cursor-pointer ${
                      isSyncing
                        ? 'bg-accent-assistant/20 text-accent-assistant cursor-wait'
                        : 'bg-accent-assistant text-white hover:bg-accent-assistant/90 shadow-sm shadow-accent-assistant/25'
                    }`}
                  >
                    {isSyncing ? (
                      <>
                        <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                        <span>Syncing...</span>
                      </>
                    ) : (
                      <>
                        <Play className="w-3.5 h-3.5" />
                        <span>Sync Now</span>
                      </>
                    )}
                  </button>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="text-center py-6 border border-dashed border-border-primary rounded-xl text-text-secondary text-xs">
            No knowledge sources registered in this workspace yet.
          </div>
        )}

        {/* Add Source Form */}
        <form onSubmit={handleAddSource} className="border-t border-border-primary/50 pt-6 space-y-4">
          <div className="flex items-center space-x-2 text-xs font-bold text-text-primary">
            <Plus className="w-4 h-4 text-accent-assistant" />
            <span>Add Ingestion Source</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1">
              <label className="text-[10px] font-bold text-text-secondary uppercase">Source Name</label>
              <input
                type="text"
                value={newSourceName}
                onChange={(e) => setNewSourceName(e.target.value)}
                placeholder="e.g. Obsidian Vault"
                className="w-full bg-background-primary text-text-primary text-xs rounded-lg px-3 py-2 border border-border-primary focus:outline-none focus:border-accent-assistant"
              />
            </div>
            <div className="space-y-1">
              <label className="text-[10px] font-bold text-text-secondary uppercase">Location / Path / URL</label>
              <input
                type="text"
                value={newSourceLocation}
                onChange={(e) => setNewSourceLocation(e.target.value)}
                placeholder="e.g. /Users/username/Vault"
                className="w-full bg-background-primary text-text-primary text-xs rounded-lg px-3 py-2 border border-border-primary focus:outline-none focus:border-accent-assistant"
              />
            </div>
            <div className="space-y-1">
              <label className="text-[10px] font-bold text-text-secondary uppercase">Kind</label>
              <select
                value={newSourceKind}
                onChange={(e) => setNewSourceKind(e.target.value)}
                className="w-full bg-background-primary text-text-primary text-xs rounded-lg px-3 py-2 border border-border-primary focus:outline-none focus:border-accent-assistant"
              >
                <option value="filesystem">Filesystem (local directory)</option>
                <option value="github">GitHub Repository</option>
                <option value="notion">Notion Workspace</option>
                <option value="youtube">YouTube Channel</option>
              </select>
            </div>
            <div className="space-y-1">
              <label className="text-[10px] font-bold text-text-secondary uppercase">Provider ID</label>
              <select
                value={newSourceProvider}
                onChange={(e) => setNewSourceProvider(e.target.value)}
                className="w-full bg-background-primary text-text-primary text-xs rounded-lg px-3 py-2 border border-border-primary focus:outline-none focus:border-accent-assistant"
              >
                <option value="markdown">Obsidian / Markdown Provider</option>
              </select>
            </div>
          </div>
          <div className="flex justify-end">
            <button
              type="submit"
              className="bg-accent-assistant hover:bg-accent-assistant/90 text-white text-xs font-bold rounded-lg px-4 py-2 flex items-center space-x-2 cursor-pointer shadow-sm shadow-accent-assistant/20"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Register Source</span>
            </button>
          </div>
        </form>
      </div>

      {/* Runtimes and pipeline status */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Processing Stages */}
        <div className="p-5 rounded-2xl border border-border-primary bg-surface-card space-y-4">
          <div className="flex items-center space-x-2">
            <Activity className="w-4 h-4 text-accent-assistant" />
            <span className="font-bold text-sm text-text-primary">Pipeline Transformations</span>
          </div>
          <div className="space-y-2">
            {diagnostics?.active_stages.map((stage) => (
              <div key={stage.id} className="flex items-center justify-between text-xs py-1.5 border-b border-border-primary/20 last:border-0">
                <span className="font-medium text-text-primary">{stage.name}</span>
                <span className="text-[9px] px-1.5 py-0.5 rounded bg-accent-memory/10 text-accent-memory font-bold font-mono">
                  Order {stage.order}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Sync History / Audit Card */}
        <div className="p-5 rounded-2xl border border-border-primary bg-surface-card space-y-4">
          <div className="flex items-center space-x-2">
            <Info className="w-4 h-4 text-accent-assistant" />
            <span className="font-bold text-sm text-text-primary">Last Ingestion Run</span>
          </div>
          {diagnostics?.last_sync_run ? (
            <div className="space-y-3 text-xs">
              <div className="flex justify-between">
                <span className="text-text-secondary">Provider</span>
                <span className="font-bold text-text-primary">{diagnostics.last_sync_run.provider}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-secondary">Status</span>
                <span className={`font-bold uppercase ${diagnostics.last_sync_run.status === 'success' ? 'text-accent-memory' : 'text-accent-video'}`}>
                  {diagnostics.last_sync_run.status}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-secondary">Timestamp</span>
                <span className="text-text-primary font-mono">{new Date(diagnostics.last_sync_run.completed_at || diagnostics.last_sync_run.started_at).toLocaleString()}</span>
              </div>
              <div className="grid grid-cols-3 gap-2 text-center pt-2 border-t border-border-primary/20">
                <div>
                  <div className="text-[9px] text-text-secondary font-bold">Created</div>
                  <div className="font-extrabold text-accent-memory">{diagnostics.last_sync_run.objects_created}</div>
                </div>
                <div>
                  <div className="text-[9px] text-text-secondary font-bold">Updated</div>
                  <div className="font-extrabold text-text-primary">{diagnostics.last_sync_run.objects_updated}</div>
                </div>
                <div>
                  <div className="text-[9px] text-text-secondary font-bold">Missing</div>
                  <div className="font-extrabold text-accent-video">{diagnostics.last_sync_run.objects_missing}</div>
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-8 text-text-secondary text-xs italic">
              No sync runs recorded yet.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
