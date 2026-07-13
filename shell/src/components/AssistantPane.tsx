import React, { useEffect, useState } from 'react';
import { useWorkspace } from '../services/workspaceState';
import { MessageSquare, Sparkles, AlertCircle, Brain, BookOpen, FileText, Link2 } from 'lucide-react';
import { api } from '../services/api';
import type { ObjectDetailsResponse, ConceptDetailResponse } from '../services/api';
import { Link } from 'react-router-dom';

export const AssistantPane: React.FC<{ className?: string }> = ({ className }) => {
  const { state } = useWorkspace();
  const [memoryContext, setMemoryContext] = useState<ObjectDetailsResponse | null>(null);
  const [conceptContext, setConceptContext] = useState<ConceptDetailResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  useEffect(() => {
    const fetchContext = async () => {
      setMemoryContext(null);
      setConceptContext(null);
      
      if (state.selectedObjectId) {
        setLoading(true);
        try {
          const res = await api.getMemoryDetails(state.selectedObjectId);
          setMemoryContext(res);
        } catch (err) {
          console.error("Failed to load memory context for assistant", err);
        } finally {
          setLoading(false);
        }
      } else if (state.selectedConcept) {
        setLoading(true);
        try {
          const res = await api.getConceptDetails(state.selectedConcept);
          setConceptContext(res);
        } catch (err) {
          console.error("Failed to load concept context for assistant", err);
        } finally {
          setLoading(false);
        }
      }
    };
    fetchContext();
  }, [state.selectedObjectId, state.selectedConcept]);

  const renderContextContent = () => {
    if (loading) {
      return (
        <div className="flex flex-col items-center justify-center py-12 space-y-3 animate-pulse">
          <Sparkles className="w-5 h-5 text-accent-assistant animate-spin" />
          <span className="text-[10px] text-text-secondary">Loading context details...</span>
        </div>
      );
    }

    if (memoryContext) {
      const formattedDate = memoryContext.created_at ? new Date(memoryContext.created_at).toLocaleDateString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      }) : '';

      // Dynamic Metadata Fields Extraction
      let metadataFields: { label: string; value: string }[] = [];
      try {
        const meta = JSON.parse(memoryContext.metadata_json || '{}');
        Object.entries(meta).forEach(([key, val]) => {
          if (key === 'tags' || key === 'concepts') return; // Skip tags/concepts here
          if (typeof val === 'string' || typeof val === 'number' || typeof val === 'boolean') {
            const label = key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
            metadataFields.push({ label, value: val.toString() });
          } else if (Array.isArray(val)) {
            const label = key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
            metadataFields.push({ label, value: val.join(', ') });
          }
        });
      } catch {
        // ignore parsing failures
      }

      return (
        <div className="space-y-5 animate-fade-in">
          {/* Active Context Card */}
          <div className="p-3.5 rounded-xl border border-border-primary bg-background-primary/40 space-y-3">
            <div className="flex items-center space-x-2 text-[10px] font-bold text-accent-assistant uppercase tracking-wider">
              <BookOpen className="w-3.5 h-3.5 text-accent-assistant" />
              <span>Active Memory Context</span>
            </div>
            <h4 className="text-xs font-bold text-text-primary leading-snug">{memoryContext.title}</h4>
            
            {/* Source Details & Timestamps */}
            <div className="space-y-1.5 text-[10px] text-text-secondary pt-1 border-t border-border-primary/50">
              <div className="flex justify-between">
                <span className="font-semibold text-text-primary/70">Type</span>
                <span className="capitalize">{memoryContext.type}</span>
              </div>
              <div className="flex justify-between">
                <span className="font-semibold text-text-primary/70">Source Provider</span>
                <span className="capitalize">{memoryContext.source}</span>
              </div>
              {formattedDate && (
                <div className="flex justify-between">
                  <span className="font-semibold text-text-primary/70">Indexed On</span>
                  <span>{formattedDate}</span>
                </div>
              )}
            </div>

            {/* File Properties */}
            {metadataFields.length > 0 && (
              <div className="space-y-1 text-[10px] text-text-secondary border-t border-border-primary/50 pt-2">
                <span className="font-bold text-text-primary/70 block uppercase tracking-wider text-[9px] mb-1">Properties</span>
                {metadataFields.map((field, idx) => (
                  <div key={idx} className="flex justify-between items-start space-x-2">
                    <span className="font-semibold text-text-primary/60 shrink-0">{field.label}</span>
                    <span className="truncate text-right select-all">{field.value}</span>
                  </div>
                ))}
              </div>
            )}

            {/* File Path info */}
            {memoryContext.location && (
              <div className="text-[9px] text-text-secondary border-t border-border-primary/50 pt-2 space-y-1">
                <span className="font-bold text-text-primary/70 block uppercase tracking-wider text-[9px]">File Path</span>
                <div className="flex items-center space-x-1 p-1 bg-background-primary rounded border border-border-primary/50 min-w-0">
                  <Link2 className="w-3 h-3 text-text-secondary/70 shrink-0" />
                  <span className="truncate font-mono select-all text-text-primary">{memoryContext.location}</span>
                </div>
              </div>
            )}
          </div>

          {/* Connected Concepts (Relationships) */}
          <div className="space-y-2">
            <h4 className="text-[10px] font-bold text-text-secondary uppercase tracking-widest px-1">
              Connected Concepts
            </h4>
            {memoryContext.connected_concepts.length > 0 ? (
              <div className="flex flex-wrap gap-1.5 p-1">
                {memoryContext.connected_concepts.map((concept) => (
                  <Link
                    key={concept.id}
                    to={`/concepts/${encodeURIComponent(concept.title)}`}
                    className="px-2.5 py-1 rounded-md text-[10px] font-bold border border-border-primary bg-surface-card hover:border-accent-concept/30 text-text-secondary hover:text-accent-concept transition-all cursor-pointer flex items-center space-x-1"
                  >
                    <Brain className="w-2.5 h-2.5 text-accent-concept" />
                    <span>{concept.title}</span>
                  </Link>
                ))}
              </div>
            ) : (
              <p className="text-[10px] italic text-text-secondary/50 px-1">No connected concepts extracted.</p>
            )}
          </div>

          {/* Actions Placeholder (Max 3) */}
          <div className="space-y-2 border-t border-border-primary/50 pt-4">
            <h4 className="text-[10px] font-bold text-text-secondary uppercase tracking-widest px-1">
              Actions
            </h4>
            <div className="space-y-1.5">
              <button
                disabled
                className="w-full flex items-center justify-between px-3 py-2 rounded-lg border border-border-primary/40 bg-background-primary/10 text-text-secondary/60 text-xs font-medium cursor-not-allowed select-none transition-all"
              >
                <span>Summarize Content</span>
                <span className="text-[8px] font-bold bg-background-primary px-1.5 py-0.5 rounded text-text-secondary/40 border border-border-primary">Soon</span>
              </button>
              <button
                disabled
                className="w-full flex items-center justify-between px-3 py-2 rounded-lg border border-border-primary/40 bg-background-primary/10 text-text-secondary/60 text-xs font-medium cursor-not-allowed select-none transition-all"
              >
                <span>Extract Action Items</span>
                <span className="text-[8px] font-bold bg-background-primary px-1.5 py-0.5 rounded text-text-secondary/40 border border-border-primary">Soon</span>
              </button>
              <button
                disabled
                className="w-full flex items-center justify-between px-3 py-2 rounded-lg border border-border-primary/40 bg-background-primary/10 text-text-secondary/60 text-xs font-medium cursor-not-allowed select-none transition-all"
              >
                <span>Explain Semantic Link</span>
                <span className="text-[8px] font-bold bg-background-primary px-1.5 py-0.5 rounded text-text-secondary/40 border border-border-primary">Soon</span>
              </button>
            </div>
          </div>
        </div>
      );
    }

    if (conceptContext) {
      return (
        <div className="space-y-5 animate-fade-in">
          {/* Active Context Card */}
          <div className="p-3.5 rounded-xl border border-border-primary bg-background-primary/40 space-y-2">
            <div className="flex items-center space-x-2 text-[10px] font-bold text-accent-assistant uppercase tracking-wider">
              <Brain className="w-3.5 h-3.5 text-accent-concept" />
              <span>Active Concept Context</span>
            </div>
            <h4 className="text-xs font-bold text-text-primary leading-snug">{conceptContext.concept.title}</h4>
            
            <div className="space-y-1.5 text-[10px] text-text-secondary pt-1 border-t border-border-primary/50">
              <div className="flex justify-between">
                <span className="font-semibold text-text-primary/70">Governance Status</span>
                <span className="capitalize">{conceptContext.concept.status}</span>
              </div>
            </div>
          </div>

          {/* Related Memories */}
          <div className="space-y-2">
            <h4 className="text-[10px] font-bold text-text-secondary uppercase tracking-widest px-1">
              Connected Memories
            </h4>
            {conceptContext.connected_memories.length > 0 ? (
              <div className="space-y-1.5">
                {conceptContext.connected_memories.map((m) => (
                  <Link
                    key={m.id}
                    to={`/memories/${m.uuid}`}
                    className="w-full flex items-center space-x-2 px-2.5 py-2 rounded-lg border border-border-primary/60 hover:border-accent-primary/20 bg-background-primary/30 hover:bg-surface-card text-left transition-all cursor-pointer block"
                  >
                    <FileText className="w-3 h-3 text-text-secondary shrink-0" />
                    <span className="text-[10px] font-semibold text-text-secondary hover:text-text-primary truncate flex-1">{m.title}</span>
                  </Link>
                ))}
              </div>
            ) : (
              <p className="text-[10px] italic text-text-secondary/50 px-1">No memories linked to this concept.</p>
            )}
          </div>

          {/* Actions Placeholder (Max 3) */}
          <div className="space-y-2 border-t border-border-primary/50 pt-4">
            <h4 className="text-[10px] font-bold text-text-secondary uppercase tracking-widest px-1">
              Actions
            </h4>
            <div className="space-y-1.5">
              <button
                disabled
                className="w-full flex items-center justify-between px-3 py-2 rounded-lg border border-border-primary/40 bg-background-primary/10 text-text-secondary/60 text-xs font-medium cursor-not-allowed select-none transition-all"
              >
                <span>Find Related Memories</span>
                <span className="text-[8px] font-bold bg-background-primary px-1.5 py-0.5 rounded text-text-secondary/40 border border-border-primary">Soon</span>
              </button>
              <button
                disabled
                className="w-full flex items-center justify-between px-3 py-2 rounded-lg border border-border-primary/40 bg-background-primary/10 text-text-secondary/60 text-xs font-medium cursor-not-allowed select-none transition-all"
              >
                <span>Graph Expansion</span>
                <span className="text-[8px] font-bold bg-background-primary px-1.5 py-0.5 rounded text-text-secondary/40 border border-border-primary">Soon</span>
              </button>
            </div>
          </div>
        </div>
      );
    }

    return (
      <div className="flex flex-col items-center justify-center py-20 text-center space-y-4 px-4 animate-fade-in">
        <div className="p-3.5 rounded-full bg-accent-assistant/10 text-accent-assistant">
          <MessageSquare className="w-5 h-5" />
        </div>
        <div className="space-y-1">
          <h4 className="text-xs font-bold text-text-primary">No Context Supplied</h4>
          <p className="text-[10px] text-text-secondary leading-relaxed max-w-[200px] mx-auto">
            Select a memory card or explore a concept in the Conscious Workspace to feed active context to the assistant.
          </p>
        </div>
      </div>
    );
  };

  return (
    <aside className={`h-full bg-surface-card/65 backdrop-blur-md border-l border-border-primary flex flex-col select-none overflow-hidden ${className || ''}`}>
      {/* Pane Header */}
      <div className="p-4 border-b border-border-primary flex items-center justify-between shrink-0 bg-surface-card/40">
        <div className="flex items-center space-x-2">
          <MessageSquare className="w-4 h-4 text-accent-assistant" />
          <h3 className="font-extrabold text-base tracking-tight text-text-primary">
            AI Assistant
          </h3>
        </div>
        <span className="flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[9px] font-bold bg-accent-assistant/10 text-accent-assistant border border-accent-assistant/10">
          <span className="w-1 h-1 rounded-full bg-accent-assistant animate-pulse" />
          <span>Local Ready</span>
        </span>
      </div>

      {/* Pane Body */}
      <div className="flex-1 overflow-y-auto p-4 min-h-0 space-y-5">
        {(memoryContext || conceptContext) && (
          <div className="p-3.5 rounded-xl bg-accent-assistant/5 border border-accent-assistant/15 text-accent-assistant flex items-start space-x-2.5 animate-fade-in">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <h5 className="text-[10px] font-bold uppercase tracking-wider leading-none">Status</h5>
              <p className="text-[10px] text-text-secondary leading-relaxed">
                Chat intelligence coming soon. Below is the active workspace context being supplied to the AI engine:
              </p>
            </div>
          </div>
        )}
        
        {renderContextContent()}
      </div>

      {/* Pane Footer Input Panel */}
      <div className="p-4 border-t border-border-primary shrink-0 bg-surface-card/40">
        <div className="relative">
          <input
            type="text"
            disabled
            placeholder="Chat intelligence coming soon..."
            className="w-full pl-3 pr-8 py-2.5 rounded-xl border border-border-primary bg-background-primary/30 text-xs font-medium text-text-secondary cursor-not-allowed select-none"
          />
          <button
            disabled
            className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 rounded-lg text-text-secondary/50 cursor-not-allowed"
          >
            <Sparkles className="w-3.5 h-3.5 animate-pulse" />
          </button>
        </div>
      </div>
    </aside>
  );
};
