import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../services/api';
import type { ConceptDetailResponse } from '../services/api';
import { MemoryCard } from '../components/MemoryCard';
import { ArrowLeft, AlertCircle, Brain, Award, Sparkles } from 'lucide-react';

export const ConceptDetail: React.FC = () => {
  const { name } = useParams<{ name: string }>();
  const [data, setData] = useState<ConceptDetailResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDetails = async () => {
    if (!name) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.getConceptDetails(name);
      setData(res);
    } catch (err: any) {
      setError(err.message || 'Failed to load concept details');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDetails();
  }, [name]);

  // 1. Loading State
  if (loading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-6 w-32 bg-surface-card rounded" />
        <div className="p-6 rounded-2xl border border-border-primary bg-surface-card space-y-4">
          <div className="flex justify-between items-center">
            <div className="flex items-center space-x-3">
              <div className="w-12 h-12 rounded-xl bg-background-primary" />
              <div className="h-6 w-40 bg-background-primary rounded" />
            </div>
            <div className="w-20 h-6 bg-background-primary rounded-full" />
          </div>
          <div className="h-4 w-48 bg-background-primary rounded mt-4" />
        </div>
      </div>
    );
  }

  // 2. Error State
  if (error || !data) {
    return (
      <div className="space-y-6">
        <Link to="/graph" className="flex items-center space-x-2 text-sm font-semibold text-text-secondary hover:text-text-primary transition-colors">
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Knowledge</span>
        </Link>
        <div className="flex flex-col items-center justify-center py-16 text-center border border-border-primary rounded-3xl bg-surface-card p-6 max-w-md mx-auto">
          <div className="p-4 rounded-full bg-accent-concept/10 text-accent-concept mb-5">
            <AlertCircle className="w-12 h-12" />
          </div>
          <h3 className="text-xl font-bold text-text-primary">Failed to Load Concept</h3>
          <p className="text-text-secondary mt-2 text-sm leading-relaxed">
            {error || 'Concept detail record was not found.'}
          </p>
          <button
            onClick={fetchDetails}
            className="mt-6 px-5 py-2.5 bg-accent-concept text-white rounded-xl font-semibold shadow-md shadow-accent-concept/20 hover:bg-accent-concept/95 transition-all text-sm cursor-pointer"
          >
            Retry Loading
          </button>
        </div>
      </div>
    );
  }

  const { concept, connected_memories } = data;

  // Extract status and type from metadata
  let status = 'candidate';
  let type = 'unknown';
  try {
    const meta = JSON.parse(concept.metadata_json || '{}');
    status = meta.concept_status || 'candidate';
    type = meta.concept_type || 'unknown';
  } catch {
    // fallback
  }

  const isApproved = status === 'approved';

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Navigation Back Context */}
      <Link 
        to="/graph" 
        className="flex items-center space-x-2 text-sm font-semibold text-text-secondary hover:text-text-primary transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        <span>Back to Knowledge</span>
      </Link>

      {/* Main Concept Header */}
      <div className="p-6 md:p-8 rounded-2xl border border-border-primary bg-surface-card shadow-sm space-y-4">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div className="flex items-center space-x-4">
            <div className="p-3.5 rounded-xl bg-accent-concept/10 text-accent-concept shrink-0">
              <Brain className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-2xl font-extrabold text-text-primary tracking-tight leading-none">
                {concept.title}
              </h2>
              <p className="text-xs font-semibold text-text-secondary mt-2.5">
                Class: <span className="capitalize text-text-primary">{type}</span>
              </p>
            </div>
          </div>

          <div className={`px-3 py-1 rounded-full text-xs font-semibold flex items-center space-x-1 border ${
            isApproved 
              ? 'bg-accent-concept/10 text-accent-concept border-accent-concept/10' 
              : 'bg-background-primary text-text-secondary border-border-primary'
          }`}>
            {isApproved ? <Award className="w-3.5 h-3.5" /> : <Sparkles className="w-3.5 h-3.5" />}
            <span className="capitalize">{status}</span>
          </div>
        </div>
      </div>

      {/* Connected Memories Section */}
      <section className="space-y-4">
        <h3 className="text-xl font-bold text-text-primary tracking-tight">Connected Memories</h3>
        
        {connected_memories && connected_memories.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {connected_memories.map((memory) => (
              <MemoryCard key={memory.id} memory={memory} />
            ))}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-16 text-center border border-border-primary rounded-3xl bg-surface-card p-6">
            <p className="text-text-secondary text-sm">
              No human knowledge sources are linked to this concept.
            </p>
          </div>
        )}
      </section>
    </div>
  );
};
