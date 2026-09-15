import React, { useState } from 'react';
import { ArrowRight, ArrowLeft, Settings2, ShieldAlert } from 'lucide-react';

interface ConfigurationStageProps {
  onNext: (location: string, exclusions: string[]) => void;
  onBack: () => void;
}

export const ConfigurationStage: React.FC<ConfigurationStageProps> = ({ onNext, onBack }) => {
  const [location, setLocation] = useState<string>('');
  const [exclusions, setExclusions] = useState<string>('');
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!location.trim()) {
      setError('Please provide a valid directory path.');
      return;
    }
    setError(null);
    const exclusionList = exclusions
      .split('\n')
      .map((item) => item.trim())
      .filter((item) => item.length > 0);
    onNext(location.trim(), exclusionList);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6 max-w-xl mx-auto animate-fade-in">
      <div className="space-y-2">
        <h2 className="text-xl font-bold tracking-tight text-text-primary">Source Parameters Configuration</h2>
        <p className="text-xs text-text-secondary">
          Configure the path to your folder. DeepCore needs read access to index the directory.
        </p>
      </div>

      <div className="space-y-4 bg-surface-card border border-border-primary rounded-2xl p-5 shadow-sm text-sm">
        <div className="space-y-1.5">
          <label htmlFor="folderPath" className="block text-xs font-bold text-text-primary uppercase tracking-wider">
            Directory Path
          </label>
          <input
            id="folderPath"
            type="text"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            placeholder="/Users/username/vaults/personal-notes"
            className="w-full px-3.5 py-2.5 rounded-xl border border-border-primary bg-background-primary text-text-primary text-xs focus:outline-none focus:ring-1 focus:ring-accent-primary"
          />
          <p className="text-[10px] text-text-secondary">
            Use the absolute path to your notes or document workspace folder.
          </p>
        </div>

        {error && (
          <div className="flex items-center space-x-2 p-3.5 rounded-xl border border-accent-important/20 bg-accent-important/5 text-accent-important text-xs">
            <ShieldAlert className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <div className="border-t border-border-primary pt-4 space-y-2">
          <div className="flex items-center space-x-2 text-xs font-bold text-text-primary">
            <Settings2 className="w-4 h-4" />
            <span>Exclusions (Advanced Glob Expressions)</span>
          </div>
          <textarea
            value={exclusions}
            onChange={(e) => setExclusions(e.target.value)}
            placeholder="**/Archive/**&#10;**/*.tmp&#10;private_note.md"
            rows={3}
            className="w-full px-3.5 py-2.5 rounded-xl border border-border-primary bg-background-primary text-text-primary text-xs focus:outline-none focus:ring-1 focus:ring-accent-primary font-mono leading-relaxed"
          />
          <p className="text-[10px] text-text-secondary">
            Provide one glob pattern per line. Files matching these patterns will not be scanned or indexed.
          </p>
        </div>
      </div>

      <div className="flex justify-between items-center pt-2">
        <button
          type="button"
          onClick={onBack}
          className="flex items-center space-x-2 px-4 py-2 border border-border-primary rounded-xl text-xs font-bold text-text-secondary hover:text-text-primary hover:bg-background-primary transition-all cursor-pointer"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back</span>
        </button>

        <button
          type="submit"
          className="flex items-center space-x-2 px-5 py-2.5 bg-accent-primary text-white rounded-xl text-xs font-bold shadow-md shadow-accent-primary/10 hover:bg-accent-primary/95 transition-all cursor-pointer"
        >
          <span>Configure Connector</span>
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </form>
  );
};
