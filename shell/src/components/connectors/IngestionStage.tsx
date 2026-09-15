import React, { useEffect, useState } from 'react';
import { Loader2, ShieldAlert, Ban } from 'lucide-react';
import { api } from '../../services/api';
import type { SyncStatus } from '../../services/api';

interface IngestionStageProps {
  location: string;
  providerId: string;
  onNext: (status: SyncStatus) => void;
  onCancel: () => void;
}

export const IngestionStage: React.FC<IngestionStageProps> = ({ location, providerId, onNext, onCancel }) => {
  const [runId, setRunId] = useState<string | null>(null);
  const [status, setStatus] = useState<SyncStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cancelling, setCancelling] = useState<boolean>(false);

  const startSync = async () => {
    setError(null);
    try {
      const res = await api.triggerConnectorSync(providerId, location);
      setRunId(res.run_id);
      setStatus(res);
    } catch (err: any) {
      setError(err.message || 'Failed to trigger synchronization.');
    }
  };

  useEffect(() => {
    startSync();
  }, [location, providerId]);

  useEffect(() => {
    if (!runId) return;

    let intervalId: any = null;
    const pollStatus = async () => {
      try {
        const currentStatus = await api.getConnectorSyncStatus(runId);
        setStatus(currentStatus);
        
        if (currentStatus.state === 'completed') {
          clearInterval(intervalId);
          setTimeout(() => {
            onNext(currentStatus);
          }, 800);
        } else if (currentStatus.state === 'failed') {
          clearInterval(intervalId);
          setError(currentStatus.errors.join('\n') || 'Synchronization run failed.');
        } else if (currentStatus.state === 'cancelled') {
          clearInterval(intervalId);
          onCancel();
        }
      } catch (err: any) {
        console.error('Polling sync status failed', err);
      }
    };

    intervalId = setInterval(pollStatus, 500);
    return () => clearInterval(intervalId);
  }, [runId]);

  const handleCancelSync = async () => {
    if (!runId) return;
    setCancelling(true);
    try {
      await api.cancelConnectorSync(runId);
      onCancel();
    } catch (err: any) {
      setError(err.message || 'Failed to cancel synchronization.');
      setCancelling(false);
    }
  };

  return (
    <div className="space-y-6 max-w-xl mx-auto animate-fade-in">
      <div className="space-y-2">
        <h2 className="text-xl font-bold tracking-tight text-text-primary">Ingesting Knowledge Base</h2>
        <p className="text-xs text-text-secondary">
          DeepCore is parsing and building the relationship graph. This runs in the background.
        </p>
      </div>

      <div className="bg-surface-card border border-border-primary rounded-2xl p-6 shadow-sm space-y-6 min-h-[220px] flex flex-col justify-center">
        {error ? (
          <div className="flex flex-col items-center justify-center space-y-4 text-center">
            <ShieldAlert className="w-10 h-10 text-accent-important animate-pulse" />
            <div className="space-y-1 max-w-sm mx-auto">
              <h4 className="font-bold text-sm text-text-primary text-accent-important">Ingestion Error</h4>
              <p className="text-xs text-text-secondary whitespace-pre-line">{error}</p>
            </div>
            <button
              onClick={startSync}
              className="px-4 py-2 border border-border-primary rounded-xl text-xs font-bold text-text-primary hover:bg-background-primary transition-all cursor-pointer"
            >
              Retry Ingestion
            </button>
          </div>
        ) : !status ? (
          <div className="flex flex-col items-center justify-center space-y-4">
            <Loader2 className="w-8 h-8 text-accent-primary animate-spin" />
            <p className="text-xs text-text-secondary">Initializing ingestion database context...</p>
          </div>
        ) : (
          <div className="space-y-5">
            <div className="flex items-center justify-between text-xs font-bold">
              <span className="text-text-primary flex items-center space-x-2">
                <Loader2 className="w-4 h-4 text-accent-primary animate-spin" />
                <span>Syncing files...</span>
              </span>
              <span className="text-text-secondary">{status.progress.toFixed(0)}%</span>
            </div>

            <div className="w-full h-2 rounded-full bg-background-primary overflow-hidden">
              <div
                style={{ width: `${status.progress}%` }}
                className="h-full bg-accent-primary rounded-full transition-all duration-300"
              />
            </div>

            <div className="space-y-1">
              <div className="flex justify-between text-[10px] text-text-secondary font-medium uppercase tracking-wider">
                <span>Processed: {status.processed} / {status.total}</span>
                <span>Active path</span>
              </div>
              <p className="text-xs font-mono text-text-primary bg-background-primary/50 border border-border-primary/60 px-3 py-2 rounded-lg truncate">
                {status.current_artifact || 'Scanning files...'}
              </p>
            </div>
          </div>
        )}
      </div>

      <div className="flex justify-end pt-2">
        {status && status.state === 'running' && (
          <button
            onClick={handleCancelSync}
            disabled={cancelling}
            className="flex items-center space-x-2 px-4 py-2.5 border border-accent-important/20 text-accent-important hover:bg-accent-important/5 rounded-xl text-xs font-bold transition-all cursor-pointer"
          >
            <Ban className="w-4 h-4" />
            <span>{cancelling ? 'Cancelling...' : 'Cancel Sync'}</span>
          </button>
        )}
      </div>
    </div>
  );
};
