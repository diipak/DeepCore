import React, { useState } from 'react';
import { 
  CheckCircle, 
  RotateCcw, 
  Database, 
  FileText, 
  Brain, 
  Globe, 
  Share2, 
  Image, 
  Compass, 
  ShieldCheck,
  ArrowLeft
} from 'lucide-react';
import type { Message, ConversationState } from '../services/api';
import { CanvasGraphView } from './CanvasGraphView';

export type CanvasTab = 'evidence' | 'web_search' | 'graph' | 'media';

interface WorkspaceCanvasProps {
  session: ConversationState | null;
  selectedMessage: Message | null;
  onResetToLatest: () => void;
  onBackToChat?: () => void;
  className?: string;
}

export const WorkspaceCanvas: React.FC<WorkspaceCanvasProps> = ({
  session,
  selectedMessage,
  onResetToLatest,
  onBackToChat,
  className = '',
}) => {
  const [activeTab, setActiveTab] = useState<CanvasTab>('evidence');

  // Derive active message (explicitly selected or fallback to latest assistant turn)
  const latestAssistantMessage = session?.messages
    ?.filter((m) => m.role === 'assistant')
    ?.slice(-1)[0] || null;

  const currentMessage = selectedMessage || latestAssistantMessage;
  const isViewingHistorical = selectedMessage && latestAssistantMessage && selectedMessage.uuid !== latestAssistantMessage.uuid;
  const evidenceList = currentMessage?.evidence || [];

  // Source Badge derived strictly from relationship_path[0]
  const renderSourceBadge = (path: string[]) => {
    const rawSource = (path && path.length > 0 ? path[0] : 'unknown').toLowerCase();
    switch (rawSource) {
      case 'openmemory':
        return (
          <span className="flex items-center space-x-1 px-1.5 py-0.5 rounded bg-blue-500/10 border border-blue-500/20 text-[9px] font-bold text-blue-400">
            <Database className="w-2.5 h-2.5" />
            <span>OpenMemory</span>
          </span>
        );
      case 'note':
        return (
          <span className="flex items-center space-x-1 px-1.5 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/20 text-[9px] font-bold text-emerald-400">
            <FileText className="w-2.5 h-2.5" />
            <span>Vault Note</span>
          </span>
        );
      case 'concept':
        return (
          <span className="flex items-center space-x-1 px-1.5 py-0.5 rounded bg-purple-500/10 border border-purple-500/20 text-[9px] font-bold text-purple-400">
            <Brain className="w-2.5 h-2.5" />
            <span>Concept</span>
          </span>
        );
      case 'tool': {
        const toolName = (path && path.length > 1 ? path[1] : 'tool').toLowerCase();
        if (toolName.includes('duckduckgo') || toolName.includes('brave') || toolName.includes('search')) {
          return (
            <span className="flex items-center space-x-1 px-1.5 py-0.5 rounded bg-amber-500/10 border border-amber-500/20 text-[9px] font-bold text-amber-400">
              <Globe className="w-2.5 h-2.5" />
              <span>{path[1] || 'Web Search'}</span>
            </span>
          );
        }
        if (toolName.includes('file') || toolName.includes('directory')) {
          return (
            <span className="flex items-center space-x-1 px-1.5 py-0.5 rounded bg-teal-500/10 border border-teal-500/20 text-[9px] font-bold text-teal-400">
              <FileText className="w-2.5 h-2.5" />
              <span>{path[1] || 'Filesystem'}</span>
            </span>
          );
        }
        return (
          <span className="flex items-center space-x-1 px-1.5 py-0.5 rounded bg-amber-500/10 border border-amber-500/20 text-[9px] font-bold text-amber-400">
            <ShieldCheck className="w-2.5 h-2.5" />
            <span>{path[1] || 'Tool'}</span>
          </span>
        );
      }
      default:
        return (
          <span className="flex items-center space-x-1 px-1.5 py-0.5 rounded bg-slate-500/10 border border-slate-500/20 text-[9px] font-bold text-slate-400">
            <ShieldCheck className="w-2.5 h-2.5" />
            <span className="capitalize">{rawSource}</span>
          </span>
        );
    }
  };

  return (
    <div className={`h-full flex flex-col bg-surface-card/30 border-l border-border-primary select-none overflow-hidden ${className}`}>
      {/* Extensible Canvas Tab Bar */}
      <div className="px-3 pt-2 pb-0 border-b border-border-primary/60 bg-surface-card/40 flex items-center justify-between shrink-0 gap-2 overflow-x-auto">
        <div className="flex items-center space-x-1 shrink-0">
          {/* Mobile Back Button */}
          {onBackToChat && (
            <button
              type="button"
              onClick={onBackToChat}
              className="md:hidden flex items-center space-x-1 px-2.5 py-1 mr-1 rounded-lg text-[11px] font-bold text-accent-assistant bg-accent-assistant/10 hover:bg-accent-assistant/20 cursor-pointer shrink-0 transition-colors"
              title="Return to conversation"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Chat</span>
            </button>
          )}

          {/* Active Tab: Evidence */}
          <button
            onClick={() => setActiveTab('evidence')}
            className={`px-3 py-1.5 border-b-2 font-bold text-[10px] tracking-wider uppercase transition-colors cursor-pointer flex items-center space-x-1.5 shrink-0 ${
              activeTab === 'evidence'
                ? 'border-accent-assistant text-accent-assistant'
                : 'border-transparent text-text-secondary hover:text-text-primary'
            }`}
          >
            <CheckCircle className="w-3 h-3 text-emerald-500" />
            <span>Evidence ({evidenceList.length})</span>
          </button>

          {/* Future Tab Stubs (Extensible Architecture) */}
          <button
            disabled
            title="Web Search results canvas (Phase 4.1)"
            className="px-2.5 py-1.5 border-b-2 border-transparent text-[10px] font-bold text-text-secondary/40 flex items-center space-x-1 cursor-not-allowed shrink-0"
          >
            <Globe className="w-2.5 h-2.5" />
            <span>Search</span>
            <span className="text-[7.5px] px-1 py-0.2 rounded bg-border-primary/50 text-text-secondary/60">Soon</span>
          </button>

          <button
            onClick={() => setActiveTab('graph')}
            className={`px-3 py-1.5 border-b-2 font-bold text-[10px] tracking-wider uppercase transition-colors cursor-pointer flex items-center space-x-1.5 shrink-0 ${
              activeTab === 'graph'
                ? 'border-purple-400 text-purple-400'
                : 'border-transparent text-text-secondary hover:text-text-primary'
            }`}
          >
            <Share2 className="w-3 h-3 text-purple-400" />
            <span>Graph</span>
          </button>

          <button
            disabled
            title="Media & Generative Assets (Phase 4.3)"
            className="px-2.5 py-1.5 border-b-2 border-transparent text-[10px] font-bold text-text-secondary/40 flex items-center space-x-1 cursor-not-allowed shrink-0"
          >
            <Image className="w-2.5 h-2.5" />
            <span>Media</span>
            <span className="text-[7.5px] px-1 py-0.2 rounded bg-border-primary/50 text-text-secondary/60">Soon</span>
          </button>
        </div>

        {isViewingHistorical && (
          <button
            onClick={onResetToLatest}
            className="flex items-center space-x-1 px-2 py-1 rounded text-[9px] font-bold text-accent-assistant bg-accent-assistant/10 hover:bg-accent-assistant/20 cursor-pointer transition-colors shrink-0"
            title="Return to viewing latest assistant response evidence"
          >
            <RotateCcw className="w-2.5 h-2.5" />
            <span>Latest</span>
          </button>
        )}
      </div>

      {/* Canvas Body */}
      <div className="flex-1 overflow-y-auto p-3 min-h-0 space-y-3">
        {activeTab === 'graph' ? (
          <CanvasGraphView session={session} currentMessage={currentMessage} />
        ) : (
          <>
            {/* Active Inspection Target Banner */}
        <div className="p-2.5 rounded-xl border border-border-primary/60 bg-background-primary/30 flex items-start justify-between">
          <div className="space-y-0.5 min-w-0">
            <div className="flex items-center space-x-1 text-[9px] font-bold text-text-secondary uppercase tracking-wider">
              <span>{isViewingHistorical ? 'Inspecting Past Turn' : 'Active Turn Evidence'}</span>
            </div>
            <p className="text-[10px] text-text-primary font-medium truncate">
              {currentMessage ? currentMessage.content.slice(0, 60) + '...' : 'No active message'}
            </p>
          </div>
          {isViewingHistorical && (
            <span className="shrink-0 text-[8.5px] font-bold px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
              Historical
            </span>
          )}
        </div>

        {/* Evidence Citations List */}
        {evidenceList.length > 0 ? (
          <div className="space-y-2.5">
            {evidenceList.map((ev, idx) => (
              <div
                key={idx}
                className="p-3 rounded-xl border border-border-primary/80 bg-surface-card/60 space-y-2 shadow-xs hover:border-accent-assistant/30 transition-colors"
              >
                {/* Header: Source badge + Confidence score */}
                <div className="flex items-center justify-between">
                  {renderSourceBadge(ev.relationship_path)}
                  {ev.confidence && (
                    <span className="text-[9px] font-bold text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/15">
                      {(ev.confidence * 100).toFixed(0)}% Match
                    </span>
                  )}
                </div>

                {/* Relationship Path */}
                {ev.relationship_path && ev.relationship_path.length > 0 && (
                  <div className="text-[9px] text-text-secondary/80 font-mono flex items-center space-x-1 overflow-hidden truncate">
                    <span>Path:</span>
                    <span className="text-text-primary font-semibold truncate">
                      {ev.relationship_path.join(' ➔ ')}
                    </span>
                  </div>
                )}

                {/* Grounding Excerpt / Justification */}
                <div className="p-2 rounded-lg bg-background-primary/50 border border-border-primary/40 text-[10.5px] leading-relaxed text-text-secondary font-medium select-text">
                  {ev.reason}
                </div>
              </div>
            ))}
          </div>
        ) : (
          /* Empty / Zero Citations State */
          <div className="py-12 px-4 text-center space-y-2 border border-dashed border-border-primary rounded-2xl bg-surface-card/20">
            <ShieldCheck className="w-7 h-7 text-text-secondary/40 mx-auto" />
            <h5 className="text-[11px] font-bold text-text-secondary">
              {currentMessage ? 'No Citations for this Turn' : 'No Active Thought Session'}
            </h5>
            <p className="text-[10px] text-text-secondary/70 max-w-[200px] mx-auto leading-relaxed">
              {currentMessage
                ? 'This response used direct local model knowledge or fallback reasoning.'
                : 'Start a thinking session or select an assistant message from the chat to inspect evidence.'}
            </p>
          </div>
        )}

        {/* Cognitive Context Package Summary (Fallback when idle) */}
        {!currentMessage && session && (
          <div className="p-3 rounded-xl border border-border-primary/50 bg-surface-card/30 space-y-2">
            <div className="flex items-center space-x-1.5 text-[9px] font-bold text-text-secondary uppercase tracking-wider">
              <Compass className="w-3 h-3 text-accent-assistant" />
              <span>Session Awareness</span>
            </div>
            <p className="text-[10px] text-text-secondary leading-relaxed">
              Mode: <strong className="text-text-primary capitalize">{session.active_thinking_mode.toLowerCase().replace('_', ' ')}</strong>
            </p>
            {session.focus_intent && session.focus_intent.length > 0 && (
              <div className="text-[9.5px] text-text-secondary space-y-1">
                <span className="font-semibold">Active Focus Items:</span>
                <ul className="list-disc list-inside space-y-0.5 text-text-primary">
                  {session.focus_intent.slice(0, 3).map((f, fIdx) => (
                    <li key={fIdx} className="truncate">{f.title || f.description || 'Focus item'}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </>
    )}
  </div>
    </div>
  );
};
