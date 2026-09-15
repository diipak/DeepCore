import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import type { RegistryObject } from '../services/api';
import { MemoryCard } from '../components/MemoryCard';
import { SearchInput } from '../components/SearchInput';
import { BookOpen, AlertCircle, Sparkles, RefreshCw } from 'lucide-react';

type FilterType = 'all' | 'note' | 'video' | 'document';

export const Memories: React.FC = () => {
  const [memories, setMemories] = useState<RegistryObject[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [activeType, setActiveType] = useState<FilterType>('all');

  const [syncPath, setSyncPath] = useState<string>('demo/markdown');
  const [syncing, setSyncing] = useState<boolean>(false);
  const [syncError, setSyncError] = useState<string | null>(null);
  const [syncResult, setSyncResult] = useState<any | null>(null);

  const handleSync = async () => {
    setSyncing(true);
    setSyncError(null);
    setSyncResult(null);
    try {
      const res = await api.syncProvider('markdown', syncPath);
      setSyncResult(res);
      fetchMemories();
    } catch (err: any) {
      setSyncError(err.message || 'Synchronization failed');
    } finally {
      setSyncing(false);
    }
  };

  const fetchMemories = async () => {
    setLoading(true);
    setError(null);
    try {
      // Query objects from API, passing the search query and type filter
      const res = await api.searchObjects(searchQuery, activeType);
      
      // Filter out non-knowledge sources (like concepts) on the client side just in case,
      // keeping only notes, videos, and documents.
      const knowledgeSources = res.filter(o => 
        o.object_type === 'note' || 
        o.object_type === 'video' || 
        o.object_type === 'document'
      );
      setMemories(knowledgeSources);
    } catch (err: any) {
      setError(err.message || 'Failed to load memories');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Call API when search query or active filter tab changes
    const timer = setTimeout(() => {
      fetchMemories();
    }, 200); // lightweight debounce to limit API hits on keystrokes
    return () => clearTimeout(timer);
  }, [searchQuery, activeType]);

  const filterTabs: { value: FilterType; label: string }[] = [
    { value: 'all', label: 'All' },
    { value: 'note', label: 'Notes' },
    { value: 'video', label: 'Videos' },
    { value: 'document', label: 'Documents' },
  ];

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h2 className="text-3xl font-extrabold text-text-primary tracking-tight">Memories</h2>
        <p className="text-text-secondary mt-1 text-sm font-medium">Browse and search through your personal library of knowledge.</p>
      </div>

      {/* Sync Card */}
      <div className="bg-surface-card border border-border-primary rounded-2xl p-5 shadow-sm space-y-4">
        <div className="flex items-center space-x-2">
          <div className="p-2 rounded-lg bg-accent-primary/10 text-accent-primary">
            <RefreshCw className={`w-5 h-5 ${syncing ? 'animate-spin' : ''}`} />
          </div>
          <div>
            <h3 className="text-sm font-bold text-text-primary">Sync Markdown Folder</h3>
            <p className="text-xs text-text-secondary">Ingest local markdown files into your canonical knowledge graph.</p>
          </div>
        </div>

        <div className="flex flex-col sm:flex-row gap-3">
          <input
            type="text"
            value={syncPath}
            onChange={(e) => setSyncPath(e.target.value)}
            disabled={syncing}
            className="flex-1 bg-background-primary border border-border-primary rounded-xl px-4 py-2.5 text-xs text-text-primary focus:outline-none focus:ring-1 focus:ring-accent-primary disabled:opacity-60 font-mono"
            placeholder="Absolute folder path (e.g. /path/to/notes)"
          />
          <button
            onClick={handleSync}
            disabled={syncing || !syncPath.trim()}
            className="px-5 py-2.5 bg-accent-primary text-white rounded-xl font-semibold hover:bg-accent-primary/95 transition-all text-xs cursor-pointer flex items-center justify-center space-x-2 shrink-0 disabled:opacity-60"
          >
            {syncing ? (
              <>
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                <span>Syncing...</span>
              </>
            ) : (
              <span>Sync Now</span>
            )}
          </button>
        </div>

        {syncError && (
          <div className="flex items-center space-x-2 text-xs text-red-500 bg-red-500/10 p-3 rounded-xl border border-red-500/20">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{syncError}</span>
          </div>
        )}

        {syncResult && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-background-primary/40 p-4 rounded-xl border border-border-primary/40 text-center animate-fade-in">
            <div className="space-y-1">
              <span className="text-[10px] text-text-secondary font-bold uppercase tracking-wider block">Scanned</span>
              <span className="text-lg font-extrabold text-text-primary">{syncResult.objects_scanned}</span>
            </div>
            <div className="space-y-1">
              <span className="text-[10px] text-text-secondary font-bold uppercase tracking-wider block">New</span>
              <span className="text-lg font-extrabold text-green-500">+{syncResult.objects_created}</span>
            </div>
            <div className="space-y-1">
              <span className="text-[10px] text-text-secondary font-bold uppercase tracking-wider block">Unchanged</span>
              <span className="text-lg font-extrabold text-text-primary">{syncResult.objects_existing}</span>
            </div>
            <div className="space-y-1">
              <span className="text-[10px] text-text-secondary font-bold uppercase tracking-wider block">Missing</span>
              <span className="text-lg font-extrabold text-yellow-500">{syncResult.objects_missing}</span>
            </div>
          </div>
        )}
      </div>

      {/* Explorer Controls */}
      <div className="flex flex-col sm:flex-row gap-4 justify-between items-stretch sm:items-center">
        <SearchInput 
          placeholder="Search memory title, description..." 
          onSearch={(val) => setSearchQuery(val)} 
          className="w-full sm:max-w-xs"
        />

        {/* Filter Pills */}
        <div className="flex flex-wrap gap-1 bg-surface-card p-1 rounded-xl border border-border-primary self-start">
          {filterTabs.map((tab) => (
            <button
              key={tab.value}
              onClick={() => setActiveType(tab.value)}
              className={`px-4 py-2 rounded-lg text-xs font-semibold tracking-wide transition-all cursor-pointer ${
                activeType === tab.value
                  ? 'bg-accent-primary text-white shadow-sm shadow-accent-primary/20'
                  : 'text-text-secondary hover:text-text-primary hover:bg-background-primary'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* 1. Loading State */}
      {loading && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="p-5 rounded-2xl border border-border-primary bg-surface-card animate-pulse space-y-4">
              <div className="flex items-center space-x-2">
                <div className="w-8 h-8 rounded-lg bg-background-primary" />
                <div className="h-3 w-20 bg-background-primary rounded" />
              </div>
              <div className="h-5 w-40 bg-background-primary rounded" />
              <div className="h-4 w-full bg-background-primary rounded" />
            </div>
          ))}
        </div>
      )}

      {/* 2. Error State */}
      {!loading && error && (
        <div className="flex flex-col items-center justify-center py-16 text-center border border-border-primary rounded-3xl bg-surface-card p-6 max-w-md mx-auto">
          <div className="p-4 rounded-full bg-accent-primary/10 text-accent-primary mb-4">
            <AlertCircle className="w-10 h-10" />
          </div>
          <h3 className="text-lg font-bold text-text-primary">Failed to Search Memories</h3>
          <p className="text-text-secondary mt-2 text-sm leading-relaxed">{error}</p>
          <button
            onClick={fetchMemories}
            className="mt-6 px-4 py-2 bg-accent-primary text-white rounded-xl font-semibold hover:bg-accent-primary/95 transition-colors text-xs cursor-pointer"
          >
            Retry Search
          </button>
        </div>
      )}

      {/* 3. Empty State */}
      {!loading && !error && memories.length === 0 && (
        <div className="flex flex-col items-center justify-center py-20 text-center border border-dashed border-border-primary rounded-3xl bg-surface-card p-6">
          <div className="p-4 rounded-full bg-background-primary text-text-secondary mb-4">
            {searchQuery ? <Sparkles className="w-12 h-12" /> : <BookOpen className="w-12 h-12" />}
          </div>
          <h3 className="text-lg font-bold text-text-primary">
            {searchQuery ? 'No Matching Memories' : 'No Memories Sync\'d'}
          </h3>
          <p className="text-text-secondary mt-2 max-w-sm text-sm">
            {searchQuery 
              ? `We couldn't find any results for "${searchQuery}" in your watched folder or source lists.` 
              : 'Add note files into your watched folders to get started with DeepCore.'
            }
          </p>
        </div>
      )}

      {/* 4. Populated State */}
      {!loading && !error && memories.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {memories.map((memory) => (
            <MemoryCard key={memory.id} memory={memory} />
          ))}
        </div>
      )}
    </div>
  );
};
