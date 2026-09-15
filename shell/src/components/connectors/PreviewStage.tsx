import React, { useEffect, useState } from 'react';
import { Loader2, ArrowRight, ArrowLeft, FileText, CheckCircle2, ShieldAlert } from 'lucide-react';
import { api } from '../../services/api';
import type { PreviewArtifact } from '../../services/api';

interface PreviewStageProps {
  location: string;
  providerId: string;
  onNext: () => void;
  onBack: () => void;
}

export const PreviewStage: React.FC<PreviewStageProps> = ({ location, providerId, onNext, onBack }) => {
  const [loading, setLoading] = useState<boolean>(true);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [previewItems, setPreviewItems] = useState<PreviewArtifact[]>([]);
  const [error, setError] = useState<string | null>(null);

  const fetchPreview = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.previewConnector(providerId, location);
      setTotalCount(res.total_artifacts);
      setPreviewItems(res.preview);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch preview of directory contents.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPreview();
  }, [location, providerId]);

  return (
    <div className="space-y-6 max-w-xl mx-auto animate-fade-in">
      <div className="space-y-2">
        <h2 className="text-xl font-bold tracking-tight text-text-primary">Source Discovery Preview</h2>
        <p className="text-xs text-text-secondary">
          DeepCore statelessly indexed the directory. No permanent records have been created yet.
        </p>
      </div>

      {loading ? (
        <div className="bg-surface-card border border-border-primary rounded-2xl p-10 flex flex-col items-center justify-center space-y-4 min-h-[260px]">
          <Loader2 className="w-8 h-8 text-accent-primary animate-spin" />
          <p className="text-xs text-text-secondary">Scanning directory metadata...</p>
        </div>
      ) : error ? (
        <div className="bg-surface-card border border-border-primary rounded-2xl p-6 flex flex-col items-center justify-center space-y-4 min-h-[260px] text-center">
          <ShieldAlert className="w-10 h-10 text-accent-important" />
          <p className="text-xs text-text-secondary max-w-sm mx-auto">{error}</p>
          <button
            onClick={fetchPreview}
            className="px-4 py-2 border border-border-primary rounded-xl text-xs font-bold text-text-primary hover:bg-background-primary transition-all cursor-pointer"
          >
            Retry Scan
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="flex items-center justify-between p-4 rounded-xl border border-accent-memory/25 bg-accent-memory/5 text-accent-memory text-xs font-bold">
            <div className="flex items-center space-x-2">
              <CheckCircle2 className="w-4 h-4" />
              <span>Ready for Synchronization</span>
            </div>
            <span>{totalCount} Discovered Artifacts</span>
          </div>

          <div className="bg-surface-card border border-border-primary rounded-2xl overflow-hidden shadow-sm">
            <div className="px-4 py-3 border-b border-border-primary bg-background-primary/40 flex justify-between text-[10px] font-bold text-text-secondary uppercase tracking-widest">
              <span>Artifact Location</span>
              <span>Size</span>
            </div>

            <div className="divide-y divide-border-primary max-h-[200px] overflow-y-auto select-none">
              {previewItems.length > 0 ? (
                previewItems.map((item, idx) => (
                  <div key={idx} className="flex justify-between items-center px-4 py-2.5 text-xs text-text-primary hover:bg-background-primary/30 transition-colors">
                    <div className="flex items-center space-x-2.5 min-w-0">
                      <FileText className="w-3.5 h-3.5 text-text-secondary shrink-0" />
                      <span className="truncate font-mono text-[10px] text-text-secondary">{item.location_descriptor}</span>
                    </div>
                    {item.size_bytes !== undefined && (
                      <span className="text-[10px] text-text-secondary font-medium shrink-0 ml-2">
                        {item.size_bytes > 1024
                          ? `${(item.size_bytes / 1024).toFixed(1)} KB`
                          : `${item.size_bytes} B`}
                      </span>
                    )}
                  </div>
                ))
              ) : (
                <div className="p-8 text-center text-xs text-text-secondary italic">
                  No compatible files found.
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      <div className="flex justify-between items-center pt-2">
        <button
          onClick={onBack}
          disabled={loading}
          className="flex items-center space-x-2 px-4 py-2 border border-border-primary rounded-xl text-xs font-bold text-text-secondary hover:text-text-primary hover:bg-background-primary disabled:opacity-50 transition-all cursor-pointer"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back</span>
        </button>

        <button
          onClick={onNext}
          disabled={loading || !!error || totalCount === 0}
          className="flex items-center space-x-2 px-5 py-2.5 bg-accent-primary text-white rounded-xl text-xs font-bold shadow-md shadow-accent-primary/10 hover:bg-accent-primary/95 disabled:opacity-50 transition-all cursor-pointer"
        >
          <span>Begin Ingestion</span>
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};
