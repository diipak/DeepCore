import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../services/api';
import type { ObjectDetailsResponse, ContentIndex } from '../services/api';
import { ArrowLeft, AlertCircle, Award, ShieldAlert } from 'lucide-react';
import { MarkdownViewer } from '../components/MarkdownViewer';

export const MemoryDetail: React.FC = () => {
  const { uuid } = useParams<{ uuid: string }>();
  const [details, setDetails] = useState<ObjectDetailsResponse | null>(null);
  const [content, setContent] = useState<ContentIndex | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDetails = async () => {
    if (!uuid) return;
    setLoading(true);
    setError(null);
    try {
      const detailsRes = await api.getMemoryDetails(uuid);
      setDetails(detailsRes);
      
      // Attempt to load content preview (only for supported text index files like .md)
      try {
        const contentRes = await api.getMemoryContent(uuid);
        setContent(contentRes);
      } catch (contentErr) {
        // Content index might not exist or be loaded, handle gracefully
        setContent(null);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load memory details');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDetails();
  }, [uuid]);

  // 1. Loading State
  if (loading) {
    return (
      <div className="space-y-6 animate-pulse max-w-3xl mx-auto w-full">
        <div className="h-6 w-32 bg-surface-card rounded" />
        <div className="p-6 rounded-2xl border border-border-primary bg-surface-card space-y-4">
          <div className="h-6 w-3/4 bg-background-primary rounded animate-pulse" />
          <div className="h-4 w-full bg-background-primary rounded mt-6 animate-pulse" />
          <div className="h-20 w-full bg-background-primary rounded animate-pulse" />
        </div>
      </div>
    );
  }

  // 2. Error State
  if (error || !details) {
    return (
      <div className="space-y-6 max-w-3xl mx-auto w-full">
        <Link to="/memories" className="flex items-center space-x-2 text-sm font-semibold text-text-secondary hover:text-text-primary transition-colors">
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Memories</span>
        </Link>
        <div className="flex flex-col items-center justify-center py-16 text-center border border-border-primary rounded-3xl bg-surface-card p-6 max-w-md mx-auto">
          <div className="p-4 rounded-full bg-accent-primary/10 text-accent-primary mb-5">
            <AlertCircle className="w-12 h-12" />
          </div>
          <h3 className="text-xl font-bold text-text-primary">Failed to Load Memory</h3>
          <p className="text-text-secondary mt-2 text-sm leading-relaxed">
            {error || 'Memory detail object was not found or is inactive.'}
          </p>
          <button
            onClick={fetchDetails}
            className="mt-6 px-5 py-2.5 bg-accent-primary text-white rounded-xl font-semibold shadow-md shadow-accent-primary/20 hover:bg-accent-primary/95 transition-all text-sm cursor-pointer"
          >
            Retry Loading
          </button>
        </div>
      </div>
    );
  }

  // Parse provider details from metadata_json
  let relativePath = '';
  let folder = '';
  let providerName = 'Markdown';
  if (details.metadata_json) {
    try {
      const meta = JSON.parse(details.metadata_json);
      relativePath = meta.relative_path || '';
      folder = meta.folder || '';
      providerName = meta.provider || details.source || 'Markdown';
    } catch (e) {
      // ignore
    }
  }

  return (
    <div className="space-y-6 animate-fade-in max-w-3xl mx-auto w-full select-text pb-12">
      {/* Navigation Back Context */}
      <Link 
        to="/memories" 
        className="flex items-center space-x-2 text-sm font-semibold text-text-secondary hover:text-text-primary transition-colors inline-flex"
      >
        <ArrowLeft className="w-4 h-4" />
        <span>Back to Memories</span>
      </Link>

      <div className="space-y-8 bg-surface-card border border-border-primary rounded-2xl p-6 md:p-10 shadow-sm">
        {/* Header Block */}
        <div>
          <h2 className="text-2xl md:text-3xl font-extrabold text-text-primary tracking-tight leading-tight">
            {details.title}
          </h2>
        </div>

        {/* Metadata Inspector */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-4 bg-background-primary/45 rounded-xl border border-border-primary/40 text-xs">
          <div className="space-y-1">
            <span className="text-[10px] text-text-secondary font-bold uppercase tracking-wider block">Provider</span>
            <span className="font-semibold text-text-primary capitalize">{providerName}</span>
          </div>
          <div className="space-y-1">
            <span className="text-[10px] text-text-secondary font-bold uppercase tracking-wider block">Source Name</span>
            <span className="font-semibold text-text-primary font-mono">{details.source}</span>
          </div>
          <div className="space-y-1">
            <span className="text-[10px] text-text-secondary font-bold uppercase tracking-wider block">Relative Path</span>
            <span className="font-semibold text-text-primary font-mono truncate block" title={relativePath || details.title}>
              {relativePath || `${details.title}.md`}
            </span>
          </div>
          <div className="space-y-1">
            <span className="text-[10px] text-text-secondary font-bold uppercase tracking-wider block">Imported</span>
            <span className="font-semibold text-text-primary">
              {new Date(details.created_at).toLocaleDateString()} {new Date(details.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </span>
          </div>
          <div className="col-span-full pt-2 border-t border-border-primary/20 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1">
            <div className="flex items-center space-x-1.5 min-w-0">
              <span className="text-[10px] text-text-secondary font-bold uppercase tracking-wider shrink-0">Canonical ID:</span>
              <span className="font-mono text-[10px] text-text-secondary truncate select-all">{details.uuid}</span>
            </div>
            <div className="text-[9px] text-text-secondary/50 truncate font-mono">
              Status: <span className="uppercase font-bold">{details.status}</span>
            </div>
          </div>
        </div>

        {/* Content Preview */}
        <div className="pt-2 border-t border-border-primary/60">
          {content ? (
            <div className="leading-relaxed bg-surface-card">
              <MarkdownViewer content={content.raw_text} />
            </div>
          ) : (
            <div className="p-8 text-center border border-dashed border-border-primary rounded-xl bg-background-primary/30">
              <ShieldAlert className="w-8 h-8 text-text-secondary/60 mx-auto mb-2" />
              <p className="text-xs text-text-secondary">
                No indexed text content available for this memory type. Only Markdown notes (.md) display content previews.
              </p>
            </div>
          )}
        </div>

        {/* Connected Memory Section */}
        <div className="space-y-3 pt-6 border-t border-border-primary/60">
          <h4 className="text-[10px] font-bold text-text-secondary uppercase tracking-widest">
            Connected Memory
          </h4>
          {details.referenced_objects && details.referenced_objects.length > 0 ? (
            <div className="space-y-4">
              {/* Metadata indicators */}
              <div className="flex flex-wrap gap-4 text-xs font-semibold text-text-secondary bg-background-primary/40 p-3 rounded-xl border border-border-primary/40">
                {(() => {
                  const videos = details.referenced_objects.filter(r => r.object_type === 'video').length;
                  const repos = details.referenced_objects.filter(r => r.object_type === 'repository').length;
                  const docs = details.referenced_objects.filter(r => r.object_type === 'document').length;
                  return (
                    <>
                      {videos > 0 && <span className="flex items-center space-x-1"><span>🎬</span> <span>{videos} {videos === 1 ? 'Video' : 'Videos'} discovered</span></span>}
                      {repos > 0 && <span className="flex items-center space-x-1"><span>💻</span> <span>{repos} {repos === 1 ? 'Repository' : 'Repositories'} discovered</span></span>}
                      {docs > 0 && <span className="flex items-center space-x-1"><span>🌐</span> <span>{docs} {docs === 1 ? 'Web reference' : 'Web references'} discovered</span></span>}
                    </>
                  );
                })()}
              </div>

              {/* Tree list */}
              <div className="font-mono text-sm space-y-1 text-text-secondary select-text pl-1">
                {details.referenced_objects.map((ref, idx) => {
                  const isLast = idx === details.referenced_objects!.length - 1;
                  const prefix = isLast ? '└ ' : '├ ';
                  let emoji = '🌐';
                  let label = 'Web Resource';
                  if (ref.object_type === 'video') {
                    emoji = '🎬';
                    label = 'YouTube Video';
                  } else if (ref.object_type === 'repository') {
                    emoji = '💻';
                    label = 'Repository';
                  }
                  
                  return (
                    <div key={ref.uuid} className="flex items-center space-x-2 py-0.5 hover:text-text-primary transition-colors">
                      <span className="text-text-secondary/60">{prefix}</span>
                      <span>{emoji}</span>
                      <Link
                        to={`/objects/${ref.uuid}`}
                        className="hover:underline font-medium text-text-primary"
                      >
                        {ref.title}
                      </Link>
                      <span className="text-xs text-text-secondary/50">({label})</span>
                    </div>
                  );
                })}
              </div>
            </div>
          ) : (
            <div className="p-4 rounded-xl border border-dashed border-border-primary text-center bg-background-primary/30">
              <p className="text-xs text-text-secondary font-medium">
                No connected objects discovered yet
              </p>
            </div>
          )}
        </div>

        {/* Connected Concepts */}
        <div className="space-y-3 pt-6 border-t border-border-primary/60">
          <h4 className="text-[10px] font-bold text-text-secondary uppercase tracking-widest">
            Linked Concepts
          </h4>
          {details.connected_concepts && details.connected_concepts.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {details.connected_concepts.map((concept) => (
                <Link
                  key={concept.uuid}
                  to={`/concepts/${encodeURIComponent(concept.title)}`}
                  className="px-2.5 py-1 rounded-lg text-xs font-semibold bg-accent-concept/10 text-accent-concept hover:bg-accent-concept/15 border border-accent-concept/10 transition-colors flex items-center space-x-1 cursor-pointer"
                >
                  <Award className="w-3.5 h-3.5" />
                  <span>{concept.title}</span>
                </Link>
              ))}
            </div>
          ) : (
            <div className="p-4 rounded-xl border border-dashed border-border-primary text-center bg-background-primary/30">
              <p className="text-xs text-text-secondary">
                No semantic concepts are linked to this memory object yet.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
