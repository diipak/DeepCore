import React, { useState } from 'react';
import { ShieldCheck, ShieldAlert, Key, Loader2, ArrowLeft } from 'lucide-react';
import { api } from '../../services/api';

interface AuthorizationStageProps {
  location: string;
  providerId: string;
  onNext: () => void;
  onBack: () => void;
}

export const AuthorizationStage: React.FC<AuthorizationStageProps> = ({ location, providerId, onNext, onBack }) => {
  const [checking, setChecking] = useState<boolean>(false);
  const [authorized, setAuthorized] = useState<boolean | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleVerify = async () => {
    setChecking(true);
    setError(null);
    try {
      await api.previewConnector(providerId, location);
      setAuthorized(true);
      setTimeout(() => {
        onNext();
      }, 800);
    } catch (err: any) {
      setAuthorized(false);
      setError(err.message || 'Permission Denied: Cannot access folder. Check path readability.');
    } finally {
      setChecking(false);
    }
  };

  return (
    <div className="space-y-6 max-w-xl mx-auto animate-fade-in">
      <div className="space-y-2">
        <h2 className="text-xl font-bold tracking-tight text-text-primary">System Permission Validation</h2>
        <p className="text-xs text-text-secondary">
          DeepCore is validating read permissions for the target folder.
        </p>
      </div>

      <div className="bg-surface-card border border-border-primary rounded-2xl p-6 shadow-sm flex flex-col items-center justify-center space-y-5 text-center min-h-[220px]">
        {checking ? (
          <>
            <Loader2 className="w-10 h-10 text-accent-primary animate-spin" />
            <div className="space-y-1">
              <h4 className="font-bold text-sm text-text-primary">Checking directory permissions...</h4>
              <p className="text-xs text-text-secondary">Evaluating read permissions on target path.</p>
            </div>
          </>
        ) : authorized === true ? (
          <>
            <ShieldCheck className="w-10 h-10 text-accent-action" />
            <div className="space-y-1">
              <h4 className="font-bold text-sm text-text-primary text-accent-action">Verification Successful</h4>
              <p className="text-xs text-text-secondary">Read access verified. Folder is ready for scanning.</p>
            </div>
          </>
        ) : authorized === false ? (
          <>
            <ShieldAlert className="w-10 h-10 text-accent-important animate-bounce" />
            <div className="space-y-1 max-w-sm mx-auto">
              <h4 className="font-bold text-sm text-text-primary text-accent-important">Authorization Failed</h4>
              <p className="text-xs text-text-secondary mt-1">{error}</p>
            </div>
          </>
        ) : (
          <>
            <Key className="w-10 h-10 text-accent-memory" />
            <div className="space-y-1 max-w-sm">
              <h4 className="font-bold text-sm text-text-primary">Verify Path Access</h4>
              <p className="text-xs text-text-secondary leading-relaxed mt-1">
                Confirm that the DeepCore binary has read rights to: <br />
                <code className="text-[10px] bg-background-primary px-1.5 py-0.5 rounded font-mono break-all">{location}</code>
              </p>
            </div>
          </>
        )}
      </div>

      <div className="flex justify-between items-center pt-2">
        <button
          onClick={onBack}
          disabled={checking}
          className="flex items-center space-x-2 px-4 py-2 border border-border-primary rounded-xl text-xs font-bold text-text-secondary hover:text-text-primary hover:bg-background-primary disabled:opacity-50 transition-all cursor-pointer"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back</span>
        </button>

        {authorized !== true && (
          <button
            onClick={handleVerify}
            disabled={checking}
            className="flex items-center space-x-2 px-5 py-2.5 bg-accent-primary text-white rounded-xl text-xs font-bold shadow-md shadow-accent-primary/10 hover:bg-accent-primary/95 disabled:opacity-50 transition-all cursor-pointer"
          >
            <span>Verify Permissions</span>
          </button>
        )}
      </div>
    </div>
  );
};
