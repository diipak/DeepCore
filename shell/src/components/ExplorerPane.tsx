import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import type { RegistryObject, ConceptListEntry } from '../services/api';
import { useWorkspace } from '../services/workspaceState';
import { SearchInput } from './SearchInput';
import { MemoryCard } from './MemoryCard';
import { ConceptCard } from './ConceptCard';
import { Network, MessageSquare, AlertCircle } from 'lucide-react';
import { Link } from 'react-router-dom';

export const ExplorerPane: React.FC<{ className?: string }> = ({ className }) => {
  const { state } = useWorkspace();
  const [memories, setMemories] = useState<RegistryObject[]>([]);
  const [concepts, setConcepts] = useState<ConceptListEntry[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>('');

  const loadMemories = async () => {
    setLoading(true);
    setError(null);
    try {
      const type = state.activeTypeFilter === 'all' ? undefined : state.activeTypeFilter;
      const res = await api.searchObjects(searchQuery, type);
      // Keep all objects except concepts
      let filtered = res.filter(o => o.object_type !== 'concept');
      if (state.activeSourceFilter) {
        filtered = filtered.filter(o => o.source_system.toLowerCase().includes(state.activeSourceFilter!.toLowerCase()));
      }
      setMemories(filtered);
    } catch (err: any) {
      setError(err.message || 'Failed to load memories');
    } finally {
      setLoading(false);
    }
  };

  const loadConcepts = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getConcepts(100);
      // Apply search query filtering locally if search query exists
      const filtered = searchQuery
        ? res.filter(c => c.concept.title.toLowerCase().includes(searchQuery.toLowerCase()))
        : res;
      setConcepts(filtered);
    } catch (err: any) {
      setError(err.message || 'Failed to load concepts');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const timer = setTimeout(() => {
      if (state.activeSurface === 'memories') {
        loadMemories();
      } else if (state.activeSurface === 'concepts' || state.activeSurface === 'graph') {
        loadConcepts();
      }
    }, 150);
    return () => clearTimeout(timer);
  }, [state.activeSurface, state.activeTypeFilter, state.activeSourceFilter, searchQuery]);

  // Loading indicator helper
  const renderLoading = () => (
    <div className="space-y-3 p-4 animate-pulse">
      {[...Array(4)].map((_, i) => (
        <div key={i} className="h-20 bg-background-primary rounded-xl border border-border-primary" />
      ))}
    </div>
  );

  // Error boundary helper
  const renderError = () => {
    const errorColorClass = state.activeSurface === 'concepts' || state.activeSurface === 'graph'
      ? 'text-accent-concept'
      : 'text-accent-memory';
    return (
      <div className="p-5 text-center space-y-3">
        <AlertCircle className={`w-8 h-8 mx-auto ${errorColorClass}`} />
        <p className="text-xs text-text-secondary leading-relaxed">{error}</p>
      </div>
    );
  };

  const getSectionTitle = () => {
    switch (state.activeSurface) {
      case 'memories':
        if (state.activeSourceFilter) {
          return `${state.activeSourceFilter.charAt(0).toUpperCase() + state.activeSourceFilter.slice(1)} Objects`;
        }
        return state.activeTypeFilter === 'all' ? 'All Memories' : `${state.activeTypeFilter}s`;
      case 'concepts':
        return 'Concepts';
      case 'graph':
        return 'Graph Explorer';
      case 'assistant':
        return 'AI Assistant';
      default:
        return 'Workspace';
    }
  };

  return (
    <div className={`h-full border-r border-border-primary bg-surface-card flex flex-col select-none overflow-hidden ${className || ''}`}>
      {/* Pane Header */}
      <div className="p-4 border-b border-border-primary space-y-3 shrink-0">
        <div className="flex items-center justify-between">
          <h3 className="font-extrabold text-base tracking-tight text-text-primary capitalize">
            {getSectionTitle()}
          </h3>
          <span className="text-[10px] font-bold text-text-secondary bg-background-primary px-2 py-0.5 rounded border border-border-primary">
            Explorer
          </span>
        </div>
        
        {/* Search bar (only visible if section supports exploration lists) */}
        {state.activeSurface !== 'assistant' && (
          <div className="max-w-xl">
            <SearchInput
              placeholder={`Search ${state.activeSurface}...`}
              onSearch={setSearchQuery}
              className="w-full"
            />
          </div>
        )}
      </div>

      {/* Pane Body list explorer */}
      <div className="flex-1 overflow-y-auto min-h-0">
        {loading ? (
          renderLoading()
        ) : error ? (
          renderError()
        ) : (
          <>
            {/* MEMORIES SECTION LIST */}
            {state.activeSurface === 'memories' && (
              <div className="p-4 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {memories.length > 0 ? (
                  memories.map(m => (
                    <MemoryCard key={m.id} memory={m} />
                  ))
                ) : (
                  <div className="py-12 text-center text-xs text-text-secondary col-span-full">
                    No memories found.
                  </div>
                )}
              </div>
            )}

            {/* CONCEPTS SECTION LIST */}
            {state.activeSurface === 'concepts' && (
              <div className="p-4 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {concepts.length > 0 ? (
                  concepts.map(c => (
                    <ConceptCard key={c.concept.id} entry={c} />
                  ))
                ) : (
                  <div className="py-12 text-center text-xs text-text-secondary col-span-full">
                    No concepts found.
                  </div>
                )}
              </div>
            )}

            {/* GRAPH SECTION LIST */}
            {state.activeSurface === 'graph' && (
              <div className="p-4 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {concepts.length > 0 ? (
                  concepts.map(entry => {
                    const isSelected = state.activeSurface === 'graph' && state.selectedConcept === entry.concept.title;
                    return (
                      <Link
                        key={entry.concept.id}
                        to={`/graph/${encodeURIComponent(entry.concept.title)}`}
                        className={`w-full flex items-center justify-between p-3.5 rounded-xl border text-left transition-all block cursor-pointer group ${
                          isSelected
                            ? 'border-accent-concept bg-accent-concept/5 shadow-sm'
                            : 'border-border-primary hover:border-accent-concept/20 bg-surface-card'
                        }`}
                      >
                        <div className="flex items-center space-x-2.5 min-w-0">
                          <Network className={`w-4 h-4 shrink-0 ${isSelected ? 'text-accent-concept' : 'text-text-secondary'}`} />
                          <span className={`text-xs font-bold truncate ${isSelected ? 'text-accent-concept' : 'text-text-primary'}`}>
                            {entry.concept.title}
                          </span>
                        </div>
                        <span className="text-[10px] text-text-secondary shrink-0 font-medium bg-background-primary px-1.5 py-0.5 rounded border border-border-primary">
                          {entry.connection_count} links
                        </span>
                      </Link>
                    );
                  })
                ) : (
                  <div className="py-12 text-center text-xs text-text-secondary col-span-full">
                    No concepts mapped.
                  </div>
                )}
              </div>
            )}

            {/* ASSISTANT SECTION MENU */}
            {state.activeSurface === 'assistant' && (
              <div className="p-4 space-y-4 text-center">
                <div className="p-3.5 rounded-xl bg-accent-assistant/5 border border-accent-assistant/10 text-accent-assistant inline-block">
                  <MessageSquare className="w-6 h-6" />
                </div>
                <div>
                  <h4 className="text-xs font-bold text-text-primary">Chat Context Mode</h4>
                  <p className="text-[11px] text-text-secondary mt-1 leading-relaxed">
                    Assistant panel is ready on the right column. Use it to converse with notes and graphs.
                  </p>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};
