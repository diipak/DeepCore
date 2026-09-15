import React from 'react';
import { ArrowRight, ShieldAlert } from 'lucide-react';
import type { SyncStatus } from '../../services/api';

interface VerificationStageProps {
  status: SyncStatus | null;
  onNext: () => void;
}

export const VerificationStage: React.FC<VerificationStageProps> = ({ status, onNext }) => {
  return (
    <div className="space-y-6 max-w-xl mx-auto animate-fade-in">
      <div className="space-y-2">
        <h2 className="text-xl font-bold tracking-tight text-text-primary">Synchronization Complete</h2>
        <p className="text-xs text-text-secondary">
          DeepCore finished synchronizing your source. Review the metrics report.
        </p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl border border-border-primary bg-surface-card text-center space-y-1">
          <span className="text-[10px] font-bold text-text-secondary uppercase tracking-wider block">Total Scanned</span>
          <span className="text-xl font-extrabold text-text-primary">{status?.total || 0}</span>
        </div>

        <div className="p-4 rounded-xl border border-border-primary bg-surface-card text-center space-y-1">
          <span className="text-[10px] font-bold text-text-secondary uppercase tracking-wider block">New Ingested</span>
          <span className="text-xl font-extrabold text-accent-action">{status?.processed || 0}</span>
        </div>

        <div className="p-4 rounded-xl border border-border-primary bg-surface-card text-center space-y-1">
          <span className="text-[10px] font-bold text-text-secondary uppercase tracking-wider block">Warnings</span>
          <span className="text-xl font-extrabold text-accent-warning">{status?.warnings?.length || 0}</span>
        </div>

        <div className="p-4 rounded-xl border border-border-primary bg-surface-card text-center space-y-1">
          <span className="text-[10px] font-bold text-text-secondary uppercase tracking-wider block">Errors</span>
          <span className="text-xl font-extrabold text-accent-important">{status?.errors?.length || 0}</span>
        </div>
      </div>

      {status && status.errors && status.errors.length > 0 && (
        <div className="bg-accent-important/5 border border-accent-important/20 text-accent-important text-xs rounded-xl p-4 space-y-2 max-h-[120px] overflow-y-auto font-mono leading-relaxed">
          <div className="flex items-center space-x-2 font-bold">
            <ShieldAlert className="w-4 h-4 shrink-0" />
            <span>Ingestion Errors</span>
          </div>
          <ul className="list-disc pl-5 space-y-1 text-[11px] list-none">
            {status.errors.map((err, idx) => (
              <li key={idx}>{err}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="flex justify-end pt-2">
        <button
          onClick={onNext}
          className="flex items-center space-x-2 px-5 py-2.5 bg-accent-primary text-white rounded-xl text-xs font-bold shadow-md shadow-accent-primary/10 hover:bg-accent-primary/95 transition-all cursor-pointer"
        >
          <span>Acknowledge & Finalize</span>
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};
