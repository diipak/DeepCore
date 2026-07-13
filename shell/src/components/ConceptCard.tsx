import React from 'react';
import { Brain, Award, Sparkles } from 'lucide-react';
import type { ConceptListEntry } from '../services/api';

import { Link } from 'react-router-dom';

interface ConceptCardProps {
  entry: ConceptListEntry;
}

export const ConceptCard: React.FC<ConceptCardProps> = ({ entry }) => {
  const { concept, connection_count } = entry;
  let status = 'candidate';
  try {
    const meta = JSON.parse(concept.metadata_json || '{}');
    status = meta.concept_status || 'candidate';
  } catch {
    // fallback
  }

  const isApproved = status === 'approved';

  return (
    <Link 
      to={`/concepts/${encodeURIComponent(concept.title)}`}
      className="p-4 rounded-xl border border-border-primary bg-surface-card transition-all duration-200 shadow-sm flex items-center justify-between hover:shadow-md hover:border-accent-concept/20 block cursor-pointer group"
    >
      <div className="flex items-center space-x-3">
        <div className="p-2.5 rounded-lg bg-background-primary text-text-secondary group-hover:bg-accent-concept/10 group-hover:text-accent-concept transition-colors">
          <Brain className="w-5 h-5" />
        </div>
        <div>
          <h4 className="font-semibold text-text-primary text-base group-hover:text-accent-concept transition-colors">{concept.title}</h4>
          <p className="text-xs text-text-secondary mt-0.5">{connection_count} {connection_count === 1 ? 'connection' : 'connections'}</p>
        </div>
      </div>
      <div className={`px-2.5 py-1 rounded-full text-xs font-semibold flex items-center space-x-1 ${
        isApproved 
          ? 'bg-accent-concept/15 text-accent-concept' 
          : 'bg-background-primary text-text-secondary border border-border-primary'
      }`}>
        {isApproved ? <Award className="w-3.5 h-3.5" /> : <Sparkles className="w-3.5 h-3.5" />}
        <span className="capitalize">{status}</span>
      </div>
    </Link>
  );
};

