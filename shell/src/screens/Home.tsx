import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../services/api';
import type { DashboardResponse, RegistryObject } from '../services/api';
import { ConceptCard } from '../components/ConceptCard';
import { MemoryCard } from '../components/MemoryCard';
import { SearchInput } from '../components/SearchInput';
import { RefreshCw, AlertCircle, Database, Sparkles, Brain, FileText, Video } from 'lucide-react';

export const Home: React.FC = () => {
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [searchResults, setSearchResults] = useState<RegistryObject[]>([]);
  const [searching, setSearching] = useState<boolean>(false);

  const fetchDashboardData = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getDashboard();
      setData(res);
    } catch (err: any) {
      setError(err.message || 'Failed to load second brain details');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const handleSearch = async (value: string) => {
    setSearchQuery(value);
    if (!value.trim()) {
      setSearchResults([]);
      return;
    }
    setSearching(true);
    try {
      const res = await api.searchObjects(value, undefined, 20);
      setSearchResults(res);
    } catch (err) {
      console.error('Search failed:', err);
    } finally {
      setSearching(false);
    }
  };

  // 1. Loading State
  if (loading) {
    return (
      <div className="space-y-10 py-4">
        <div>
          <div className="h-8 w-48 bg-surface-card rounded animate-pulse" />
          <div className="h-4 w-64 bg-surface-card rounded animate-pulse mt-2" />
        </div>

        {/* Search Bar Skeleton */}
        <div className="h-12 max-w-xl bg-surface-card rounded-xl animate-pulse" />

        {/* Main Body Skeleton */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2 space-y-4">
            <div className="h-6 w-36 bg-surface-card rounded animate-pulse" />
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
          </div>
          <div className="space-y-4">
            <div className="h-6 w-36 bg-surface-card rounded animate-pulse" />
            <div className="space-y-3">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="p-4 rounded-xl border border-border-primary bg-surface-card animate-pulse flex justify-between items-center">
                  <div className="flex items-center space-x-3">
                    <div className="w-10 h-10 rounded-lg bg-background-primary" />
                    <div className="space-y-2">
                      <div className="h-4 w-28 bg-background-primary rounded" />
                      <div className="h-3 w-16 bg-background-primary rounded" />
                    </div>
                  </div>
                  <div className="w-16 h-6 rounded-full bg-background-primary" />
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  // 2. Error State
  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center max-w-md mx-auto">
        <div className="p-4 rounded-full bg-accent-primary/10 text-accent-primary mb-5">
          <AlertCircle className="w-12 h-12" />
        </div>
        <h3 className="text-xl font-bold text-text-primary">Intelligence Connection Failed</h3>
        <p className="text-text-secondary mt-2 leading-relaxed text-sm">
          We encountered an error while connecting to your local memory library: <span className="font-semibold">{error}</span>
        </p>
        <button
          onClick={fetchDashboardData}
          className="mt-6 flex items-center space-x-2 px-5 py-2.5 bg-accent-primary text-white rounded-xl font-semibold shadow-md shadow-accent-primary/20 hover:bg-accent-primary/95 transition-all text-sm cursor-pointer"
        >
          <RefreshCw className="w-4 h-4" />
          <span>Try Connecting Again</span>
        </button>
      </div>
    );
  }

  // 3. Empty State
  const hasMemories = data && data.summary.memory_count > 0;
  if (!data || !hasMemories) {
    return (
      <div className="space-y-10 py-4">
        <div>
          <h2 className="text-3xl font-extrabold text-text-primary tracking-tight">Personal Intelligence</h2>
          <p className="text-text-secondary mt-1 text-sm font-medium">An overview of your personal second brain.</p>
        </div>

        <div className="flex flex-col items-center justify-center py-20 text-center max-w-md mx-auto border border-dashed border-border-primary rounded-3xl bg-surface-card p-8">
          <div className="p-4 rounded-full bg-background-primary text-text-secondary mb-5">
            <Database className="w-12 h-12" />
          </div>
          <h3 className="text-xl font-bold text-text-primary">Your Private Memory is Empty</h3>
          <p className="text-text-secondary mt-2 leading-relaxed text-sm">
            DeepCore hasn't synchronized any knowledge files yet. Add some Markdown notes to your watched directory or capture a YouTube video to initialize the knowledge engine.
          </p>
          <button
            onClick={fetchDashboardData}
            className="mt-6 flex items-center space-x-2 px-5 py-2.5 bg-accent-primary text-white rounded-xl font-semibold hover:bg-accent-primary/95 transition-all text-sm cursor-pointer"
          >
            <RefreshCw className="w-4 h-4" />
            <span>Check for Updates</span>
          </button>
        </div>
      </div>
    );
  }

  const { summary, top_concepts, recent_memories } = data;

  // 4. Populated State
  return (
    <div className="space-y-10 pb-6 animate-fade-in py-4 max-w-5xl mx-auto">
      {/* Calm Awareness Header */}
      <header className="flex flex-col md:flex-row md:items-center md:justify-between border-b border-border-primary pb-6 space-y-4 md:space-y-0">
        <div>
          <div className="flex items-center space-x-2.5">
            <h2 className="text-3xl font-extrabold text-text-primary tracking-tight">Welcome Back</h2>
            <span className="flex items-center space-x-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-accent-memory/10 text-accent-memory border border-accent-memory/10">
              <span className="w-1.5 h-1.5 rounded-full bg-accent-memory animate-pulse" />
              <span>Private Memory Active</span>
            </span>
          </div>
          <p className="text-text-secondary mt-2 text-sm font-medium">
            Your second brain currently contains <span className="font-bold text-text-primary">{summary.memory_count}</span> indexed memories and <span className="font-bold text-text-primary">{summary.concept_count}</span> semantic concepts linked across <span className="font-bold text-text-primary">{summary.relationship_count}</span> links.
          </p>
        </div>
      </header>

      {/* 1. Search/Ask Component (Raycast Style) */}
      <section className="space-y-3 max-w-2xl bg-surface-card border border-border-primary p-5 rounded-2xl shadow-sm relative">
        <div className="flex items-center space-x-2 text-accent-primary font-bold text-xs uppercase tracking-wider">
          <Sparkles className="w-4 h-4 text-accent-primary animate-pulse" />
          <span>Search & Ask</span>
        </div>
        <SearchInput
          placeholder="Search memories or type an idea..."
          onSearch={handleSearch}
          value={searchQuery}
          onChange={(e) => handleSearch(e.target.value)}
          className="w-full max-w-none"
        />

        {/* Inline Search Results Overlay */}
        {searchQuery.trim() !== '' && (
          <div className="mt-3 border-t border-border-primary pt-3 space-y-3 animate-fade-in">
            <div className="flex items-center justify-between text-[10px] text-text-secondary uppercase tracking-widest font-bold px-1">
              <span>Search Results</span>
              {searching && <span className="animate-pulse text-accent-primary text-[9px]">Searching...</span>}
            </div>

            {searchResults.length > 0 ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-h-[300px] overflow-y-auto pr-1">
                {searchResults.map((item) => {
                  const isConcept = item.object_type.toLowerCase() === 'concept';
                  const isVideo = item.object_type.toLowerCase() === 'video';
                  
                  // Setup path & color theme
                  const linkPath = isConcept 
                    ? `/concepts/${encodeURIComponent(item.title)}` 
                    : `/memories/${item.uuid}`;
                    
                  const badgeColor = isConcept 
                    ? 'bg-accent-concept/10 text-accent-concept border-accent-concept/10' 
                    : isVideo 
                      ? 'bg-accent-video/10 text-accent-video border-accent-video/10'
                      : 'bg-accent-memory/10 text-accent-memory border-accent-memory/10';

                  return (
                    <Link
                      key={item.id}
                      to={linkPath}
                      onClick={() => {
                        // Clear search on navigation
                        setSearchQuery('');
                        setSearchResults([]);
                      }}
                      className="p-3 rounded-xl border border-border-primary bg-background-primary/30 hover:bg-background-primary transition-all duration-150 flex items-center justify-between group cursor-pointer"
                    >
                      <div className="flex items-center space-x-3 min-w-0">
                        <div className="p-1.5 rounded-lg bg-surface-card border border-border-primary text-text-secondary shrink-0">
                          {isConcept ? (
                            <Brain className="w-3.5 h-3.5 text-accent-concept" />
                          ) : isVideo ? (
                            <Video className="w-3.5 h-3.5 text-accent-video" />
                          ) : (
                            <FileText className="w-3.5 h-3.5 text-accent-memory" />
                          )}
                        </div>
                        <div className="min-w-0">
                          <span className="text-xs font-bold text-text-primary block truncate group-hover:text-accent-primary transition-colors">
                            {item.title}
                          </span>
                          {item.description && (
                            <span className="text-[10px] text-text-secondary block truncate mt-0.5 max-w-xs">
                              {item.description}
                            </span>
                          )}
                        </div>
                      </div>
                      <span className={`text-[8px] font-bold uppercase tracking-wider px-2 py-0.5 rounded border shrink-0 ${badgeColor}`}>
                        {item.object_type}
                      </span>
                    </Link>
                  );
                })}
              </div>
            ) : !searching ? (
              <div className="py-6 text-center text-xs text-text-secondary">
                No matching memories or concepts found.
              </div>
            ) : null}
          </div>
        )}
        
        {searchQuery.trim() === '' && (
          <p className="text-[10px] text-text-secondary pl-1">
            Press enter or type queries to dynamically search indexed file contents and concept names.
          </p>
        )}
      </section>

      {/* 2. Main Columns: Continue & Discover */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Continue Reading Section (2/3 width) */}
        <section className="lg:col-span-2 space-y-8">
          <div className="space-y-4">
            <h3 className="text-xs font-bold text-text-secondary uppercase tracking-widest px-1">
              Continue Reading
            </h3>
            {recent_memories.length > 0 ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {recent_memories.map((memory) => (
                  <MemoryCard key={memory.id} memory={memory} />
                ))}
              </div>
            ) : (
              <div className="p-8 text-center border border-border-primary rounded-2xl bg-surface-card">
                <p className="text-text-secondary text-sm">No recent memories available.</p>
              </div>
            )}
          </div>

          <div className="space-y-4 pt-2">
            <h3 className="text-xs font-bold text-text-secondary uppercase tracking-widest px-1">
              Recently Connected
            </h3>
            {data.recently_connected && data.recently_connected.length > 0 ? (
              <div className="space-y-3.5 bg-surface-card border border-border-primary rounded-2xl p-5 shadow-sm">
                {data.recently_connected.map((entry) => {
                  const hasRepos = entry.repo_connected > 0;
                  const label = hasRepos 
                    ? `linked ${entry.repo_connected} ${entry.repo_connected === 1 ? 'repository' : 'repositories'}`
                    : `discovered ${entry.total_connected} connected ${entry.total_connected === 1 ? 'memory' : 'memories'}`;
                  
                  return (
                    <div key={entry.uuid} className="flex flex-col space-y-1.5 pb-3 border-b border-border-primary/40 last:border-0 last:pb-0 last:mb-0">
                      <Link 
                        to={`/objects/${entry.uuid}`} 
                        className="text-sm font-bold text-text-primary hover:text-accent-primary transition-colors hover:underline inline-block"
                      >
                        {entry.title}
                      </Link>
                      <div className="text-xs text-text-secondary font-mono flex items-center space-x-1.5 pl-3">
                        <span className="text-text-secondary/50">↳</span>
                        <span>{label}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="p-8 text-center border border-dashed border-border-primary rounded-2xl bg-surface-card/40">
                <p className="text-xs text-text-secondary font-medium">No recently connected memories discovered yet.</p>
              </div>
            )}
          </div>
        </section>

        {/* Discover Concepts Section (1/3 width) */}
        <section className="space-y-4">
          <h3 className="text-xs font-bold text-text-secondary uppercase tracking-widest px-1">
            Discover Connections
          </h3>
          {top_concepts.length > 0 ? (
            <div className="space-y-3">
              {top_concepts.map((entry) => (
                <ConceptCard key={entry.concept.id} entry={entry} />
              ))}
            </div>
          ) : (
            <div className="p-8 text-center border border-border-primary rounded-2xl bg-surface-card">
              <p className="text-text-secondary text-sm">No concepts extracted yet.</p>
            </div>
          )}
        </section>
      </div>
    </div>
  );
};
