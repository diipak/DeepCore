import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import type { ConceptListEntry, ConceptDetailResponse } from '../services/api';
import { MemoryCard } from '../components/MemoryCard';
import { Brain, Network, Award, Sparkles, ArrowLeft, ChevronRight, AlertCircle, Info } from 'lucide-react';

export const Graph: React.FC = () => {
  const [concepts, setConcepts] = useState<ConceptListEntry[]>([]);
  const [selectedConcept, setSelectedConcept] = useState<string | null>(null);
  const [detailData, setDetailData] = useState<ConceptDetailResponse | null>(null);
  const [loadingList, setLoadingList] = useState<boolean>(true);
  const [loadingDetails, setLoadingDetails] = useState<boolean>(false);
  const [errorList, setErrorList] = useState<string | null>(null);
  const [errorDetails, setErrorDetails] = useState<string | null>(null);

  // Fetch list of all concepts
  const fetchConcepts = async () => {
    setLoadingList(true);
    setErrorList(null);
    try {
      const res = await api.getConcepts(100);
      setConcepts(res);
    } catch (err: any) {
      setErrorList(err.message || 'Failed to load concepts list');
    } finally {
      setLoadingList(false);
    }
  };

  // Fetch details of a selected concept
  const fetchConceptDetails = async (name: string) => {
    setLoadingDetails(true);
    setErrorDetails(null);
    try {
      const res = await api.getConceptDetails(name);
      setDetailData(res);
    } catch (err: any) {
      setErrorDetails(err.message || `Failed to explore connections for "${name}"`);
    } finally {
      setLoadingDetails(false);
    }
  };

  useEffect(() => {
    fetchConcepts();
  }, []);

  useEffect(() => {
    if (selectedConcept) {
      fetchConceptDetails(selectedConcept);
    } else {
      setDetailData(null);
    }
  }, [selectedConcept]);

  // Handle mobile-friendly concept select
  const handleSelect = (name: string) => {
    setSelectedConcept(name);
  };

  // 1. Loading State (Full Screen List Loading)
  if (loadingList) {
    return (
      <div className="space-y-6">
        <div>
          <div className="h-8 w-48 bg-surface-card rounded animate-pulse" />
          <div className="h-4 w-72 bg-surface-card rounded animate-pulse mt-2" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 animate-pulse">
          <div className="space-y-3">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-14 bg-surface-card rounded-xl border border-border-primary" />
            ))}
          </div>
          <div className="md:col-span-2 h-96 bg-surface-card rounded-2xl border border-border-primary" />
        </div>
      </div>
    );
  }

  // 2. Error State (Concepts List Fail)
  if (errorList) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center max-w-md mx-auto">
        <div className="p-4 rounded-full bg-accent-primary/10 text-accent-primary mb-5">
          <AlertCircle className="w-12 h-12" />
        </div>
        <h3 className="text-xl font-bold text-text-primary">Failed to Load Concepts</h3>
        <p className="text-text-secondary mt-2 text-sm leading-relaxed">{errorList}</p>
        <button
          onClick={fetchConcepts}
          className="mt-6 px-5 py-2.5 bg-accent-primary text-white rounded-xl font-semibold shadow-md shadow-accent-primary/20 hover:bg-accent-primary/95 transition-all text-sm cursor-pointer"
        >
          Retry
        </button>
      </div>
    );
  }

  // 3. Empty State (No concepts synchronized at all)
  if (concepts.length === 0) {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="text-3xl font-extrabold text-text-primary tracking-tight">Knowledge Explorer</h2>
          <p className="text-text-secondary mt-1 text-sm font-medium">Explore visual relationships and connections between your concepts.</p>
        </div>
        <div className="flex flex-col items-center justify-center py-20 text-center border border-dashed border-border-primary rounded-3xl bg-surface-card p-6">
          <div className="p-4 rounded-full bg-background-primary text-text-secondary mb-4">
            <Network className="w-12 h-12" />
          </div>
          <h3 className="text-lg font-bold text-text-primary">No extracted concepts</h3>
          <p className="text-text-secondary mt-2 max-w-sm text-sm">
            Add notes with hashtags, capitalized titles, or code references to start mapping extracted concepts in this view.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h2 className="text-3xl font-extrabold text-text-primary tracking-tight">Knowledge Explorer</h2>
        <p className="text-text-secondary mt-1 text-sm font-medium">Explore visual relationships and connections between your concepts.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-start">
        {/* Concepts Sidebar - Hidden on mobile if a concept is active for progressive details disclosure */}
        <div className={`space-y-3 ${selectedConcept ? 'hidden md:block' : 'block'}`}>
          <h3 className="text-sm font-bold text-text-secondary uppercase tracking-wider px-1">Extracted Concepts</h3>
          <div className="space-y-2 max-h-[60vh] md:max-h-[70vh] overflow-y-auto pr-1">
            {concepts.map((entry) => {
              const isSelected = selectedConcept === entry.concept.title;
              let status = 'candidate';
              try {
                const meta = JSON.parse(entry.concept.metadata_json || '{}');
                status = meta.concept_status || 'candidate';
              } catch {
                // ignore
              }
              const isApproved = status === 'approved';

              return (
                <button
                  key={entry.concept.id}
                  onClick={() => handleSelect(entry.concept.title)}
                  className={`w-full text-left p-4 rounded-xl border transition-all flex items-center justify-between cursor-pointer ${
                    isSelected
                      ? 'border-accent-primary bg-accent-primary/5 shadow-sm'
                      : 'border-border-primary bg-surface-card hover:border-accent-primary/20'
                  }`}
                >
                  <div className="flex items-center space-x-3 truncate">
                    <Brain className={`w-5 h-5 shrink-0 ${isSelected ? 'text-accent-primary' : 'text-text-secondary'}`} />
                    <div className="truncate">
                      <p className={`font-semibold text-sm truncate ${isSelected ? 'text-accent-primary' : 'text-text-primary'}`}>
                        {entry.concept.title}
                      </p>
                      <p className="text-xs text-text-secondary mt-0.5">{entry.connection_count} links</p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-1">
                    {isApproved ? (
                      <Award className="w-4 h-4 text-accent-primary shrink-0" />
                    ) : (
                      <Sparkles className="w-4 h-4 text-text-secondary shrink-0" />
                    )}
                    <ChevronRight className="w-4 h-4 text-text-secondary" />
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Tree Explorer Canvas Area */}
        <div className={`md:col-span-2 ${selectedConcept ? 'block' : 'hidden md:block'}`}>
          {selectedConcept ? (
            <div className="p-6 md:p-8 rounded-2xl border border-border-primary bg-surface-card shadow-sm space-y-6 min-h-[50vh]">
              {/* Mobile Back Header */}
              <div className="flex md:hidden items-center mb-4">
                <button
                  onClick={() => setSelectedConcept(null)}
                  className="flex items-center space-x-2 text-sm font-semibold text-text-secondary hover:text-text-primary transition-colors cursor-pointer"
                >
                  <ArrowLeft className="w-4 h-4" />
                  <span>Back to concepts list</span>
                </button>
              </div>

              {loadingDetails ? (
                <div className="flex flex-col items-center justify-center py-20 text-center animate-pulse">
                  <Brain className="w-12 h-12 text-accent-primary animate-spin" />
                  <p className="text-sm text-text-secondary mt-4">Mapping tree branches...</p>
                </div>
              ) : errorDetails ? (
                <div className="flex flex-col items-center justify-center py-20 text-center max-w-sm mx-auto">
                  <AlertCircle className="w-10 h-10 text-accent-primary mb-4" />
                  <p className="text-sm text-text-secondary leading-relaxed">{errorDetails}</p>
                </div>
              ) : detailData ? (
                <div className="space-y-8">
                  {/* Root Node rendering */}
                  <div className="flex flex-col items-center">
                    <div className="px-6 py-4 rounded-2xl border-2 border-accent-primary bg-accent-primary/5 text-accent-primary flex items-center space-x-3 shadow-md max-w-xs text-center">
                      <Brain className="w-6 h-6 shrink-0" />
                      <span className="font-extrabold text-base tracking-tight">{detailData.concept.title}</span>
                    </div>
                    {/* Trunk vertical line */}
                    {detailData.connected_memories.length > 0 && (
                      <div className="w-0.5 h-8 bg-border-primary mt-1" />
                    )}
                  </div>

                  {/* Branches layout (Tree relationship display) */}
                  {detailData.connected_memories.length > 0 ? (
                    <div className="relative pl-6 md:pl-10 space-y-4 border-l-2 border-border-primary ml-4 md:ml-12">
                      {detailData.connected_memories.map((memory) => (
                        <div key={memory.id} className="relative">
                          {/* Horizontal branch line */}
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
              ) : null}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center p-12 text-center border border-dashed border-border-primary rounded-3xl bg-surface-card min-h-[50vh]">
              <div className="p-4 rounded-full bg-background-primary text-text-secondary mb-4">
                <Info className="w-10 h-10" />
              </div>
              <h3 className="text-lg font-bold text-text-primary">Select a Concept</h3>
              <p className="text-text-secondary mt-2 max-w-xs text-sm">
                Pick an extracted concept from the list to explore its linked registry memories in a structured connection tree.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
