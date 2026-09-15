import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../services/api';
import type { DashboardResponse, RegistryObject } from '../services/api';
import { SearchInput } from '../components/SearchInput';
import { 
  RefreshCw, 
  AlertCircle, 
  Sparkles, 
  Brain, 
  FileText, 
  Video, 
  Calendar, 
  ArrowRight, 
  Clock, 
  CornerDownRight,
  PlusCircle,
  Check
} from 'lucide-react';

export const Home: React.FC = () => {
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [searchResults, setSearchResults] = useState<RegistryObject[]>([]);
  const [searching, setSearching] = useState<boolean>(false);

  // Capture State
  const [captureInput, setCaptureInput] = useState<string>('');
  const [capturing, setCapturing] = useState<boolean>(false);
  const [capturedObj, setCapturedObj] = useState<RegistryObject | null>(null);

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

  const handleCaptureSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!captureInput.trim()) return;

    setCapturing(true);
    try {
      const result = await api.capture(captureInput);
      setCapturedObj(result);
      setCaptureInput('');
      // Refresh dashboard context to show newly captured note in Focus/Timeline
      const res = await api.getDashboard();
      setData(res);
      // Auto-clear success message after 4s
      setTimeout(() => setCapturedObj(null), 4000);
    } catch (err: any) {
      console.error("Capture failed:", err);
      alert(err.message || "Failed to capture thought.");
    } finally {
      setCapturing(false);
    }
  };

  // Loading State
  if (loading) {
    return (
      <div className="space-y-10 py-6 max-w-4xl mx-auto animate-pulse">
        <div className="space-y-3">
          <div className="h-8 w-48 bg-surface-card rounded" />
          <div className="h-4 w-80 bg-surface-card rounded" />
        </div>
        <div className="space-y-4">
          <div className="h-6 w-32 bg-surface-card rounded" />
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-28 bg-surface-card rounded-2xl" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  // Error State
  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center max-w-md mx-auto">
        <div className="p-4 rounded-full bg-accent-primary/10 text-accent-primary mb-5">
          <AlertCircle className="w-12 h-12" />
        </div>
        <h3 className="text-xl font-bold text-text-primary">Context Extraction Failed</h3>
        <p className="text-text-secondary mt-2 leading-relaxed text-sm">
          We encountered an error while connecting to the private awareness engine: <span className="font-semibold">{error}</span>
        </p>
        <button
          onClick={fetchDashboardData}
          className="mt-6 flex items-center space-x-2 px-5 py-2.5 bg-accent-primary text-white rounded-xl font-semibold shadow-md hover:bg-accent-primary/95 transition-all text-sm cursor-pointer"
        >
          <RefreshCw className="w-4 h-4" />
          <span>Try Reconnecting</span>
        </button>
      </div>
    );
  }

  if (!data) return null;

  const { summary, focus, orientation, understanding, continuation } = data;

  const renderIcon = (type: string) => {
    switch (type.toLowerCase()) {
      case 'note':
        return <FileText className="w-4 h-4 text-accent-memory" />;
      case 'event':
        return <Calendar className="w-4 h-4 text-accent-video" />;
      case 'video':
        return <Video className="w-4 h-4 text-accent-video" />;
      default:
        return <Brain className="w-4 h-4 text-accent-concept" />;
    }
  };

  return (
    <div className="space-y-12 pb-12 animate-fade-in py-6 max-w-4xl mx-auto select-text">
      {/* Calm Awareness Header */}
      <header className="border-b border-border-primary/60 pb-6 flex flex-col md:flex-row justify-between items-start md:items-center space-y-3 md:space-y-0">
        <div className="space-y-1">
          <h2 className="text-3xl font-extrabold text-text-primary tracking-tight">Welcome back.</h2>
          <p className="text-text-secondary text-sm font-medium">
            Your private memory web currently connects <span className="font-bold text-text-primary">{summary.memory_count}</span> memories and <span className="font-bold text-text-primary">{summary.concept_count}</span> concepts across <span className="font-bold text-text-primary">{summary.relationship_count}</span> associations.
          </p>
        </div>
        <span className="flex items-center space-x-1.5 px-3 py-1 rounded-full text-[10px] font-bold bg-accent-memory/10 text-accent-memory border border-accent-memory/20">
          <span className="w-1.5 h-1.5 rounded-full bg-accent-memory animate-pulse" />
          <span>Memory Web Active</span>
        </span>
      </header>

      {/* PHASE 1: Recognition — Restore User Mental Context (Amendment 1) */}
      <section className="space-y-4">
        <div className="flex items-center space-x-2 text-[10px] font-bold text-text-secondary uppercase tracking-widest px-1">
          <span>1. Recognition</span>
          <span className="text-text-secondary/40 font-normal">• Where you left off</span>
        </div>
        
        {focus.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {focus.map((item, idx) => (
              <Link
                key={idx}
                to={`/memories/${item.object_uuid}`}
                className="p-5 rounded-2xl border border-border-primary bg-surface-card hover:bg-background-primary/40 hover:border-accent-primary/20 transition-all duration-200 flex flex-col justify-between group h-28 shadow-xs cursor-pointer"
              >
                <div className="flex items-center space-x-2.5">
                  <div className="p-1.5 rounded-lg bg-background-primary group-hover:bg-surface-card border border-border-primary/50">
                    {renderIcon(item.object_type)}
                  </div>
                  <span className="text-[10px] font-bold text-text-secondary uppercase tracking-wider">
                    {item.object_type}
                  </span>
                </div>
                <div className="space-y-1 mt-2">
                  <h4 className="text-sm font-bold text-text-primary group-hover:text-accent-primary transition-colors line-clamp-1">
                    {item.title}
                  </h4>
                  <p className="text-[10px] text-text-secondary font-medium">
                    Opened {item.last_accessed}
                  </p>
                </div>
              </Link>
            ))}
          </div>
        ) : (
          <div className="p-6 text-center border border-border-primary bg-surface-card rounded-2xl">
            <p className="text-xs text-text-secondary">No active focus context found. Explore memories or notes to build focus.</p>
          </div>
        )}
      </section>

      {/* PHASE 2: Orientation — Explain what changed while user was away (Amendment 1) */}
      <section className="space-y-4">
        <div className="flex items-center space-x-2 text-[10px] font-bold text-text-secondary uppercase tracking-widest px-1">
          <span>2. Orientation</span>
          <span className="text-text-secondary/40 font-normal">• What changed recently</span>
        </div>
        
        <div className="bg-surface-card border border-border-primary rounded-2xl p-5 shadow-xs">
          <div className="relative pl-6 border-l-2 border-border-primary/60 ml-2 space-y-6">
            {orientation.map((change, idx) => {
              const element = change.object_uuid ? (
                <Link 
                  to={`/memories/${change.object_uuid}`}
                  className="font-bold text-text-primary hover:text-accent-primary hover:underline"
                >
                  {change.title}
                </Link>
              ) : (
                <span className="font-bold text-text-primary">{change.title}</span>
              );

              return (
                <div key={idx} className="relative group">
                  {/* Timeline Bullet */}
                  <div className="absolute -left-[31px] top-1.5 w-2 h-2 rounded-full bg-border-primary border-4 border-surface-card group-hover:bg-accent-primary transition-colors" />
                  
                  <div className="space-y-0.5">
                    <div className="flex items-center space-x-2">
                      <span className="text-xs font-semibold text-text-primary">
                        {element}
                      </span>
                      <span className="text-[9px] font-bold text-accent-memory bg-accent-memory/10 px-1.5 py-0.5 rounded uppercase tracking-wider">
                        {change.change_type.replace('_', ' ')}
                      </span>
                    </div>
                    <p className="text-[11px] text-text-secondary font-medium">
                      {change.description}
                    </p>
                    <div className="text-[9px] text-text-secondary/60 flex items-center space-x-1 mt-1 font-mono">
                      <Clock className="w-2.5 h-2.5" />
                      <span>{change.time_ago}</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* PHASE 3: Understanding — Surfacing meaningful observations (Amendment 1) */}
      <section className="space-y-4">
        <div className="flex items-center space-x-2 text-[10px] font-bold text-text-secondary uppercase tracking-widest px-1">
          <span>3. Understanding</span>
          <span className="text-text-secondary/40 font-normal">• System observations</span>
        </div>

        {understanding.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {understanding.map((obs) => {
              const isWarning = obs.severity === 'warning';
              const cardBg = isWarning 
                ? 'bg-accent-concept/5 border-accent-concept/20 text-accent-concept' 
                : 'bg-accent-primary/5 border-accent-primary/10 text-accent-primary';
              
              return (
                <div key={obs.id} className={`p-5 rounded-2xl border flex flex-col justify-between space-y-4 shadow-xs ${cardBg}`}>
                  <div className="space-y-1.5">
                    <div className="flex items-center space-x-2 text-[10px] font-bold uppercase tracking-wider">
                      <CornerDownRight className="w-3.5 h-3.5" />
                      <span>{obs.observation_type.replace('_', ' ')}</span>
                    </div>
                    <h4 className="text-sm font-extrabold text-text-primary leading-tight">
                      {obs.title}
                    </h4>
                    <p className="text-xs text-text-secondary font-medium leading-relaxed">
                      {obs.description}
                    </p>
                  </div>

                  <div>
                    <Link
                      to={obs.action_route}
                      className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-[10px] font-bold bg-surface-card border border-border-primary hover:border-text-primary text-text-secondary hover:text-text-primary transition-all cursor-pointer"
                    >
                      <span>{obs.action_label}</span>
                      <ArrowRight className="w-3 h-3" />
                    </Link>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="p-5 border border-dashed border-border-primary bg-surface-card/30 rounded-2xl text-center">
            <p className="text-xs text-text-secondary font-medium">Your memory web is fully integrated. No unlinked thoughts or conceptual anomalies detected.</p>
          </div>
        )}
      </section>

      {/* PHASE 4: Continuation — Pre-populate Assistant & Search (Amendment 1 & 4) */}
      <section className="space-y-6 pt-4">
        <div className="flex items-center space-x-2 text-[10px] font-bold text-text-secondary uppercase tracking-widest px-1">
          <span>4. Continuation</span>
          <span className="text-text-secondary/40 font-normal">• Guided thinking & capture</span>
        </div>

        {/* Central Search Box */}
        <div className="space-y-3 bg-surface-card border border-border-primary p-6 rounded-2xl shadow-xs relative">
          <div className="flex items-center space-x-2 text-accent-primary font-bold text-xs uppercase tracking-wider">
            <Sparkles className="w-4 h-4 text-accent-primary animate-pulse" />
            <span>Search & Query Context</span>
          </div>
          <SearchInput
            placeholder="Search memories, locations, or concepts..."
            onSearch={handleSearch}
            value={searchQuery}
            onChange={(e) => handleSearch(e.target.value)}
            className="w-full max-w-none"
          />

          {/* Inline Search Results Overlay */}
          {searchQuery.trim() !== '' && (
            <div className="mt-4 border-t border-border-primary/60 pt-4 space-y-3 animate-fade-in">
              <div className="flex items-center justify-between text-[9px] text-text-secondary uppercase tracking-widest font-bold px-1">
                <span>Search Results</span>
                {searching && <span className="animate-pulse text-accent-primary">Searching...</span>}
              </div>

              {searchResults.length > 0 ? (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-h-[250px] overflow-y-auto pr-1">
                  {searchResults.map((item) => {
                    const isConcept = item.object_type.toLowerCase() === 'concept';
                    const isVideo = item.object_type.toLowerCase() === 'video';
                    
                    const linkPath = isConcept 
                      ? `/concepts/${encodeURIComponent(item.title)}` 
                      : `/memories/${item.uuid}`;

                    return (
                      <Link
                        key={item.id}
                        to={linkPath}
                        onClick={() => {
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
                              <span className="text-[10px] text-text-secondary block truncate mt-0.5">
                                {item.description}
                              </span>
                            )}
                          </div>
                        </div>
                        <span className="text-[8px] font-bold uppercase tracking-wider px-2 py-0.5 rounded border shrink-0 bg-background-primary/50 text-text-secondary">
                          {item.object_type}
                        </span>
                      </Link>
                    );
                  })}
                </div>
              ) : !searching ? (
                <div className="py-6 text-center text-xs text-text-secondary">
                  No matching memories found.
                </div>
              ) : null}
            </div>
          )}
        </div>

        {/* Next Thinking Steps deck */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {continuation.map((step, idx) => (
            <Link
              key={idx}
              to={`/assistant?prompt=${encodeURIComponent(step.prompt)}`}
              className="p-4 rounded-xl border border-border-primary bg-surface-card hover:bg-background-primary/30 hover:border-accent-assistant/20 transition-all duration-200 flex flex-col justify-between items-start space-y-3 group cursor-pointer text-left"
            >
              <span className="text-[10px] font-bold text-text-secondary block tracking-wide uppercase">
                Thinking Guide
              </span>
              <h5 className="text-xs font-bold text-text-primary group-hover:text-accent-assistant transition-colors leading-snug line-clamp-2">
                {step.title}
              </h5>
              <span className="text-[9px] font-bold text-accent-assistant flex items-center space-x-1 pt-1.5 uppercase tracking-wider">
                <span>{step.action_label}</span>
                <ArrowRight className="w-2.5 h-2.5 transition-transform group-hover:translate-x-1" />
              </span>
            </Link>
          ))}
        </div>

        {/* Quick Capture Entrance Portal */}
        <div className="bg-surface-card border border-border-primary rounded-2xl p-6 shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2 text-text-primary font-bold text-xs uppercase tracking-wider">
              <PlusCircle className="w-4 h-4 text-accent-primary" />
              <span>Quick Capture Portal</span>
            </div>
            {capturedObj && (
              <span className="flex items-center space-x-1 text-[10px] font-bold text-emerald-500 animate-fade-in bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/10">
                <Check className="w-3.5 h-3.5" />
                <span>Captured successfully</span>
              </span>
            )}
          </div>

          <form onSubmit={handleCaptureSubmit} className="space-y-3">
            <textarea
              value={captureInput}
              onChange={(e) => setCaptureInput(e.target.value)}
              placeholder="Drop an idea, write a quick note, or paste a web link/YouTube URL..."
              rows={3}
              disabled={capturing}
              className="w-full p-4 rounded-xl border border-border-primary bg-background-primary/30 text-xs font-medium text-text-primary placeholder-text-secondary focus:outline-none focus:border-accent-primary transition-all resize-none"
            />
            <div className="flex justify-end">
              <button
                type="submit"
                disabled={capturing || !captureInput.trim()}
                className="flex items-center space-x-2 px-5 py-2.5 bg-accent-primary text-white rounded-xl font-bold hover:bg-accent-primary/95 transition-all text-xs cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
              >
                {capturing ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    <span>Capturing...</span>
                  </>
                ) : (
                  <>
                    <span>Absorb Memory</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      </section>
    </div>
  );
};
