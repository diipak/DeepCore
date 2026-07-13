import React from 'react';
import { MessageSquare } from 'lucide-react';

export const Assistant: React.FC = () => {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-extrabold text-text-primary tracking-tight">AI Assistant</h2>
        <p className="text-text-secondary mt-1 text-sm font-medium">Have a context-driven conversation with your local knowledge base.</p>
      </div>

      <div className="flex flex-col items-center justify-center py-24 text-center border border-dashed border-border-primary rounded-3xl bg-surface-card p-6">
        <div className="p-4 rounded-full bg-background-primary text-text-secondary mb-4">
          <MessageSquare className="w-12 h-12" />
        </div>
        <h3 className="text-lg font-bold text-text-primary">Assistant Chat Space</h3>
        <p className="text-text-secondary mt-2 max-w-sm text-sm">
          A client-neutral chat interface targeting your offline LLM models (e.g. Ollama) will be established here in future phases.
        </p>
      </div>
    </div>
  );
};
