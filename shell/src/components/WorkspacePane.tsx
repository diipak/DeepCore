import React, { useEffect, useState } from 'react';
import { useWorkspace } from '../services/workspaceState';
import { MemoryDetail } from '../screens/MemoryDetail';
import { ConceptDetail } from '../screens/ConceptDetail';
import { Home } from '../screens/Home';
import { SystemDiagnostics } from '../screens/SystemDiagnostics';
import { Platform } from '../screens/Platform';
import { ExplorerPane } from './ExplorerPane';
import { api } from '../services/api';
import type { ConceptDetailResponse } from '../services/api';
import { MemoryCard } from './MemoryCard';
import { Brain, AlertCircle, ArrowLeft } from 'lucide-react';
import { Link } from 'react-router-dom';

export const WorkspacePane: React.FC<{ className?: string }> = ({ className }) => {
  const { state } = useWorkspace();
  const [graphData, setGraphData] = useState<ConceptDetailResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchGraphDetails = async (name: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getConceptDetails(name);
      setGraphData(res);
    } catch (err: any) {
      setError(err.message || `Failed to map connections for "${name}"`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (state.activeSurface === 'graph' && state.selectedConcept) {
      fetchGraphDetails(state.selectedConcept);
    } else {
      setGraphData(null);
    }
  }, [state.activeSurface, state.selectedConcept]);

  // Render tree layout for Graph Explorer mode
  const renderGraphExplorer = () => {
    if (loading) {
      return (
        <div className="flex flex-col items-center justify-center py-20 text-center animate-pulse">
          <Brain className="w-12 h-12 text-accent-concept animate-spin" />
          <p className="text-sm text-text-secondary mt-4">Mapping tree branches...</p>
        </div>
      );
    }

    if (error || !graphData) {
      return (
        <div className="flex flex-col items-center justify-center py-20 text-center max-w-sm mx-auto p-4">
          <AlertCircle className="w-10 h-10 text-accent-concept mb-4" />
          <p className="text-sm text-text-secondary leading-relaxed">{error || 'Unable to explore graph connections.'}</p>
        </div>
      );
    }

    return (
      <div className="space-y-6 animate-fade-in max-w-3xl mx-auto w-full select-text pb-12">
        {/* Navigation Back Context */}
        <Link 
          to="/graph" 
          className="flex items-center space-x-2 text-sm font-semibold text-text-secondary hover:text-text-primary transition-colors inline-flex"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Knowledge</span>
        </Link>

        {/* Tree Explorer Container */}
        <div className="p-6 md:p-8 rounded-2xl border border-border-primary bg-surface-card shadow-sm space-y-8 min-h-[50vh]">
          {/* Root Node */}
          <div className="flex flex-col items-center">
            <div className="px-6 py-4 rounded-2xl border-2 border-accent-concept bg-accent-concept/5 text-accent-concept flex items-center space-x-3 shadow-md max-w-xs text-center">
              <Brain className="w-6 h-6 shrink-0" />
              <span className="font-extrabold text-base tracking-tight">{graphData.concept.title}</span>
            </div>
            {graphData.connected_memories.length > 0 && (
              <div className="w-0.5 h-8 bg-border-primary mt-1" />
            )}
          </div>

          {/* Connected Memories tree branches */}
          {graphData.connected_memories.length > 0 ? (
            <div className="relative pl-6 md:pl-10 space-y-4 border-l-2 border-border-primary ml-2 md:ml-10">
              {graphData.connected_memories.map((memory) => (
                <div key={memory.id} className="relative">
                  {/* Branch Horizontal line */}
                  <div className="absolute top-1/2 -left-6 md:-left-10 w-6 md:w-10 h-0.5 bg-border-primary -translate-y-1/2" />
                  <div className="pl-2">
                    <MemoryCard memory={memory} />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <p className="text-sm text-text-secondary">No connections linked to this concept.</p>
            </div>
          )}
        </div>
      </div>
    );
  };

  const renderContent = () => {
    // 1. If at root/home, render Home Dashboard
    if (state.activeSurface === 'home') {
      return <Home />;
    }

    // 2. If active surface is system, render System Diagnostics
    if (state.activeSurface === 'system') {
      return <SystemDiagnostics />;
    }

    // 2.5. If active surface is platform, render Platform dashboard
    if (state.activeSurface === 'platform') {
      return <Platform />;
    }

    // 3. If active surface is memories and an object is selected
    if (state.activeSurface === 'memories' && state.selectedObjectId) {
      return <MemoryDetail />;
    }

    // 4. If active surface is concepts and a concept is selected
    if (state.activeSurface === 'concepts' && state.selectedConcept) {
      return <ConceptDetail />;
    }

    // 5. If active surface is graph and a concept is selected
    if (state.activeSurface === 'graph' && state.selectedConcept) {
      return renderGraphExplorer();
    }

    // 6. If no specific object or concept is selected, render the Explorer list view for that surface
    switch (state.activeSurface) {
      case 'memories':
      case 'concepts':
      case 'graph':
        return <ExplorerPane className="w-full h-full bg-background-primary border-none p-4 md:p-6" />;
      default:
        return <Home />;
    }
  };

  return (
    <main className={`h-full bg-background-primary p-4 md:p-8 ${className || ''}`}>
      {renderContent()}
    </main>
  );
};
