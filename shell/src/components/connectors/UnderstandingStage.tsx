import React from 'react';
import { Eye, EyeOff, Server, ArrowRight, ArrowLeft } from 'lucide-react';

interface UnderstandingStageProps {
  onNext: () => void;
  onBack: () => void;
}

export const UnderstandingStage: React.FC<UnderstandingStageProps> = ({ onNext, onBack }) => {
  return (
    <div className="space-y-6 max-w-xl mx-auto animate-fade-in">
      <div className="space-y-2">
        <h2 className="text-xl font-bold tracking-tight text-text-primary">Data Protection and Access Scope</h2>
        <p className="text-xs text-text-secondary">
          DeepCore values your privacy. Please review how the Filesystem connector interacts with your machine.
        </p>
      </div>

      <div className="space-y-3.5 bg-surface-card border border-border-primary rounded-2xl p-5 shadow-sm text-sm">
        <div className="flex items-start space-x-3.5">
          <div className="p-1.5 rounded-lg bg-accent-action/10 text-accent-action shrink-0">
            <Eye className="w-5 h-5" />
          </div>
          <div>
            <h4 className="font-bold text-xs text-text-primary">What we read</h4>
            <p className="text-xs text-text-secondary mt-1">
              Markdown files (`.md`, `.markdown`) inside the configured directory. This includes title metadata, headings, paragraphs, and timestamps.
            </p>
          </div>
        </div>

        <div className="flex items-start space-x-3.5 border-t border-border-primary pt-3.5">
          <div className="p-1.5 rounded-lg bg-accent-warning/10 text-accent-warning shrink-0">
            <EyeOff className="w-5 h-5" />
          </div>
          <div>
            <h4 className="font-bold text-xs text-text-primary">What we ignore</h4>
            <p className="text-xs text-text-secondary mt-1">
              Hidden files, system configuration folders (e.g. `.git`, `.obsidian`, `.trash`), and any files matching your custom ignore exclusion globs.
            </p>
          </div>
        </div>

        <div className="flex items-start space-x-3.5 border-t border-border-primary pt-3.5">
          <div className="p-1.5 rounded-lg bg-accent-primary/10 text-accent-primary shrink-0">
            <Server className="w-5 h-5" />
          </div>
          <div>
            <h4 className="font-bold text-xs text-text-primary">Where data lives</h4>
            <p className="text-xs text-text-secondary mt-1">
              Strictly on your local disk in the encrypted DeepCore SQLite database. No external servers or API calls are used.
            </p>
          </div>
        </div>
      </div>

      <div className="flex justify-between items-center pt-2">
        <button
          onClick={onBack}
          className="flex items-center space-x-2 px-4 py-2 border border-border-primary rounded-xl text-xs font-bold text-text-secondary hover:text-text-primary hover:bg-background-primary transition-all cursor-pointer"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back</span>
        </button>

        <button
          onClick={onNext}
          className="flex items-center space-x-2 px-5 py-2.5 bg-accent-primary text-white rounded-xl text-xs font-bold shadow-md shadow-accent-primary/10 hover:bg-accent-primary/95 transition-all cursor-pointer"
        >
          <span>Acknowledge & Continue</span>
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};
