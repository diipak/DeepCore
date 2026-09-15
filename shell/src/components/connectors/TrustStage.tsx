import React, { useState } from 'react';
import { ShieldCheck, RefreshCw, Trash2, ShieldAlert, ArrowLeft, Loader2 } from 'lucide-react';
import { api } from '../../services/api';
import type { ConnectorInfo } from '../../services/api';

interface TrustStageProps {
  connector: ConnectorInfo;
  onBack: () => void;
  onRefresh: () => void;
}

export const TrustStage: React.FC<TrustStageProps> = ({ connector, onBack, onRefresh }) => {
  const [disconnecting, setDisconnecting] = useState<boolean>(false);
  const [option, setOption] = useState<'purge' | 'freeze'>('freeze');
  const [confirmText, setConfirmText] = useState<string>('');
  const [syncing, setSyncing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleSyncNow = async () => {
    setSyncing(true);
    setError(null);
    try {
      await api.triggerConnectorSync(connector.provider_id, connector.location, connector.id);
      setTimeout(() => {
        onRefresh();
      }, 500);
    } catch (err: any) {
      setError(err.message || 'Failed to trigger sync run.');
    } finally {
      setSyncing(false);
    }
  };

  const handleDisconnect = async () => {
    if (confirmText !== 'DISCONNECT') return;
    setDisconnecting(true);
    setError(null);
    try {
      await api.disconnectConnector(connector.id, option);
      onBack();
    } catch (err: any) {
      setError(err.message || 'Failed to disconnect source.');
      setDisconnecting(false);
    }
  };

  return (
    <div className="space-y-6 max-w-xl mx-auto animate-fade-in text-left">
      <div className="flex items-center justify-between border-b border-border-primary pb-4">
        <div className="space-y-1">
          <h2 className="text-xl font-bold tracking-tight text-text-primary">{connector.name}</h2>
          <code className="text-[10px] font-mono text-text-secondary bg-background-primary px-2 py-0.5 rounded">{connector.location}</code>
        </div>
        <button
          onClick={onBack}
          className="flex items-center space-x-2 px-3 py-1.5 border border-border-primary rounded-xl text-xs font-bold text-text-secondary hover:text-text-primary transition-all cursor-pointer"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back</span>
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="p-5 rounded-2xl border border-border-primary bg-surface-card space-y-3">
          <span className="text-[10px] font-bold text-text-secondary uppercase tracking-wider block">Health Indicator</span>
          <div className="flex items-center space-x-2 text-accent-action">
            <ShieldCheck className="w-5 h-5 shrink-0" />
            <span className="font-extrabold text-sm uppercase tracking-wider">{connector.status}</span>
          </div>
          <p className="text-xs text-text-secondary">
            Connector is actively trusted. Files modifications are monitored.
          </p>
        </div>

        <div className="p-5 rounded-2xl border border-border-primary bg-surface-card space-y-3">
          <span className="text-[10px] font-bold text-text-secondary uppercase tracking-wider block">Synchronization</span>
          <div className="text-xs text-text-primary space-y-1">
            <p><span className="font-semibold text-text-secondary">Last run:</span> {connector.last_sync_time ? new Date(connector.last_sync_time).toLocaleString() : 'Never'}</p>
            <p><span className="font-semibold text-text-secondary">Status:</span> <span className="capitalize">{connector.last_sync_status || 'unknown'}</span></p>
          </div>
          <button
            onClick={handleSyncNow}
            disabled={syncing}
            className="flex items-center space-x-2 px-4 py-2 border border-border-primary text-xs font-bold rounded-xl hover:bg-background-primary transition-all cursor-pointer disabled:opacity-50"
          >
            {syncing ? <Loader2 className="w-4 h-4 animate-spin text-accent-primary" /> : <RefreshCw className="w-4 h-4" />}
            <span>Sync Now</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="flex items-center space-x-2 p-3.5 rounded-xl border border-accent-important/20 bg-accent-important/5 text-accent-important text-xs">
          <ShieldAlert className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <div className="p-5 rounded-2xl border border-accent-important/15 bg-accent-important/5 space-y-4">
        <div className="space-y-1">
          <h3 className="font-bold text-sm text-accent-important flex items-center space-x-2">
            <Trash2 className="w-4 h-4" />
            <span>Danger Zone — Disconnect Source</span>
          </h3>
          <p className="text-xs text-text-secondary">
            Remove this source connector. Select how DeepCore should handle existing database objects.
          </p>
        </div>

        <div className="flex space-x-3.5">
          <label className="flex items-center space-x-2.5 cursor-pointer">
            <input
              type="radio"
              name="disconnect_opt"
              checked={option === 'freeze'}
              onChange={() => setOption('freeze')}
              className="accent-accent-primary"
            />
            <div className="text-xs text-left">
              <span className="font-bold text-text-primary block">Freeze Memories</span>
              <span className="text-[10px] text-text-secondary">Keep imported notes, but remove source sync bindings.</span>
            </div>
          </label>

          <label className="flex items-center space-x-2.5 cursor-pointer">
            <input
              type="radio"
              name="disconnect_opt"
              checked={option === 'purge'}
              onChange={() => setOption('purge')}
              className="accent-accent-primary"
            />
            <div className="text-xs text-left">
              <span className="font-bold text-text-primary block">Purge Memories</span>
              <span className="text-[10px] text-text-secondary">Delete all notes and relationships imported from this directory.</span>
            </div>
          </label>
        </div>

        <div className="space-y-2 border-t border-border-primary/50 pt-3">
          <p className="text-[10px] text-text-secondary">
            To confirm this action, type <strong className="text-text-primary">DISCONNECT</strong> below.
          </p>
          <div className="flex space-x-3">
            <input
              type="text"
              value={confirmText}
              onChange={(e) => setConfirmText(e.target.value)}
              placeholder="DISCONNECT"
              className="px-3.5 py-2 rounded-xl border border-border-primary bg-surface-card text-text-primary text-xs font-mono uppercase focus:outline-none focus:ring-1 focus:ring-accent-primary"
            />
            <button
              onClick={handleDisconnect}
              disabled={confirmText !== 'DISCONNECT' || disconnecting}
              className="px-4 py-2 bg-accent-important text-white font-bold text-xs rounded-xl disabled:opacity-40 transition-all cursor-pointer"
            >
              Confirm Disconnect
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
