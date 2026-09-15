import React, { useState, useEffect, useMemo, useRef } from 'react';
import { 
  Brain, 
  Database, 
  FileText, 
  Share2, 
  Network, 
  Sparkles, 
  RotateCcw
} from 'lucide-react';
import { api } from '../services/api';
import type { 
  Message, 
  ConversationState, 
  ConceptDetailResponse, 
  ObjectDetailsResponse,
  ConceptListEntry
} from '../services/api';
import { useWorkspace } from '../services/workspaceState';

interface GraphNode {
  id: string;
  title: string;
  type: string;
  isRoot?: boolean;
  metadata?: string;
  source?: string;
}

interface GraphEdge {
  id: string;
  sourceId: string;
  targetId: string;
  label: string;
  confidence: number;
  reason?: string;
}

interface CanvasGraphViewProps {
  session: ConversationState | null;
  currentMessage: Message | null;
}

export const CanvasGraphView: React.FC<CanvasGraphViewProps> = ({ session, currentMessage }) => {
  const { state } = useWorkspace();
  
  const [activeConceptName, setActiveConceptName] = useState<string | null>(null);
  const [activeObjectUuid, setActiveObjectUuid] = useState<string | null>(null);
  const [activeEvidenceId, setActiveEvidenceId] = useState<string | null>(null);
  
  const lastMessageUuidRef = useRef<string | null>(null);

  const [conceptData, setConceptData] = useState<ConceptDetailResponse | null>(null);
  const [objectData, setObjectData] = useState<ObjectDetailsResponse | null>(null);
  const [conceptsList, setConceptsList] = useState<ConceptListEntry[]>([]);
  
  const [loading, setLoading] = useState<boolean>(false);
  const [_error, setError] = useState<string | null>(null);

  // 1. Initial entity discovery from conversation evidence / session context / workspace state
  useEffect(() => {
    // Reset evidence re-rooting when switching inspected messages
    if (currentMessage?.uuid !== lastMessageUuidRef.current) {
      lastMessageUuidRef.current = currentMessage?.uuid || null;
      setActiveEvidenceId(null);
    }

    // Do not clobber an active evidence re-rooting unless message changed
    if (activeEvidenceId) {
      return;
    }

    // Check if workspace already has an active selection
    if (state.selectedConcept) {
      setActiveConceptName(state.selectedConcept);
      setActiveObjectUuid(null);
      return;
    }
    if (state.selectedObjectId) {
      setActiveObjectUuid(state.selectedObjectId);
      setActiveConceptName(null);
      return;
    }

    // Otherwise check evidence from current inspected message
    const evidenceList = currentMessage?.evidence || [];
    for (const ev of evidenceList) {
      const path = ev.relationship_path || [];
      if (path[0]?.toLowerCase() === 'concept' && path[1]) {
        setActiveConceptName(path[1]);
        setActiveObjectUuid(null);
        return;
      }
      // Only set activeObjectUuid for non-OpenMemory targets (OpenMemory items live in external store)
      if (path[0]?.toLowerCase() !== 'openmemory' && ev.target_uuid && ev.target_uuid.length > 20) {
        setActiveObjectUuid(ev.target_uuid);
        setActiveConceptName(null);
        return;
      }
    }

    // Check session focus intent
    if (session?.focus_intent && session.focus_intent.length > 0) {
      const focus = session.focus_intent[0];
      if (focus.object_type === 'concept') {
        setActiveConceptName(focus.title);
        setActiveObjectUuid(null);
        return;
      }
      if (focus.object_uuid) {
        setActiveObjectUuid(focus.object_uuid);
        setActiveConceptName(null);
        return;
      }
    }
  }, [currentMessage, session, state.selectedConcept, state.selectedObjectId, activeEvidenceId]);

  // 2. Fetch list of available concepts in workspace for quick entity navigation
  useEffect(() => {
    const loadConcepts = async () => {
      try {
        const res = await api.getConcepts(20);
        setConceptsList(res);
      } catch {
        // Fallback silently if no concepts indexed yet
      }
    };
    loadConcepts();
  }, []);

  // 3. Fetch details when active entity changes
  useEffect(() => {
    const fetchData = async () => {
      if (activeConceptName) {
        setLoading(true);
        setError(null);
        try {
          const res = await api.getConceptDetails(activeConceptName);
          setConceptData(res);
          setObjectData(null);
        } catch {
          // Concept might not exist in SQLite (e.g. from OpenMemory or synthetic)
          setConceptData(null);
        } finally {
          setLoading(false);
        }
      } else if (activeObjectUuid) {
        setLoading(true);
        setError(null);
        try {
          const res = await api.getMemoryDetails(activeObjectUuid);
          setObjectData(res);
          setConceptData(null);
        } catch {
          // Object might be external OpenMemory UUID
          setObjectData(null);
        } finally {
          setLoading(false);
        }
      }
    };

    fetchData();
  }, [activeConceptName, activeObjectUuid]);

  // 4. Construct Node-Link Graph Model
  const { nodes, edges, rootNode } = useMemo(() => {
    const nodeList: GraphNode[] = [];
    const edgeList: GraphEdge[] = [];
    let root: GraphNode | null = null;

    // SCENARIO 0: Re-rooted on an in-hand OpenMemory / Turn Evidence Node
    if (activeEvidenceId && currentMessage?.evidence && currentMessage.evidence.length > 0) {
      const evIndex = currentMessage.evidence.findIndex((ev, idx) => {
        const id = ev.source_uuid || `ev-${idx}`;
        return id === activeEvidenceId;
      });

      if (evIndex !== -1) {
        const currentEv = currentMessage.evidence[evIndex];
        const path = currentEv.relationship_path || [];
        const targetTitle = path[1] || (currentEv.reason.length > 35 ? currentEv.reason.slice(0, 32) + '...' : currentEv.reason);
        const targetType = path[0]?.toLowerCase() || 'openmemory';

        root = {
          id: currentEv.source_uuid || `ev-${evIndex}`,
          title: targetTitle,
          type: targetType,
          metadata: currentEv.reason,
          isRoot: true,
        };
        nodeList.push(root);

        // 1. Link back to Originating Dialogue Turn
        const turnTitle = currentMessage.content.length > 40 
          ? currentMessage.content.slice(0, 36) + '...' 
          : (currentMessage.content || 'Dialogue Turn');
        const turnNode: GraphNode = {
          id: currentMessage.uuid || 'root-turn',
          title: turnTitle,
          type: 'dialogue_turn',
          metadata: 'Active assistant turn grounded by this citation (Click to return)',
        };
        nodeList.push(turnNode);
        edgeList.push({
          id: `edge-root-turn`,
          sourceId: root.id,
          targetId: turnNode.id,
          label: 'grounded_turn',
          confidence: currentEv.confidence ?? 0.9,
          reason: 'Dialogue turn that recalled and cited this memory',
        });

        // 2. Link semantic concept/domain if path has segments (e.g. ['openmemory', 'automation'])
        if (path.length > 1) {
          path.slice(1).forEach((domain, dIdx) => {
            const domainNode: GraphNode = {
              id: `domain-${dIdx}-${domain}`,
              title: domain,
              type: 'concept',
              metadata: `Knowledge category domain: ${domain}`,
            };
            nodeList.push(domainNode);
            edgeList.push({
              id: `edge-domain-${dIdx}`,
              sourceId: root!.id,
              targetId: domainNode.id,
              label: 'categorized_as',
              confidence: currentEv.confidence ?? 0.9,
            });
          });
        }

        // 3. Link other co-retrieved evidence items from this turn
        currentMessage.evidence.forEach((otherEv, oIdx) => {
          if (oIdx === evIndex) return;
          const otherPath = otherEv.relationship_path || [];
          const otherId = otherEv.source_uuid || `ev-${oIdx}`;
          const otherTitle = otherPath[1] || (otherEv.reason.length > 35 ? otherEv.reason.slice(0, 32) + '...' : otherEv.reason);
          const otherType = otherPath[0]?.toLowerCase() || 'openmemory';

          const sibNode: GraphNode = {
            id: otherId,
            title: otherTitle,
            type: otherType,
            metadata: otherEv.reason,
          };
          nodeList.push(sibNode);
          edgeList.push({
            id: `edge-co-${oIdx}`,
            sourceId: root!.id,
            targetId: sibNode.id,
            label: 'co_retrieved',
            confidence: Math.min(currentEv.confidence ?? 0.85, otherEv.confidence ?? 0.85),
            reason: 'Co-retrieved in same reasoning turn',
          });
        });

        return { nodes: nodeList, edges: edgeList, rootNode: root };
      }
    }

    // SCENARIO A: Backend Concept Detail response available
    if (conceptData) {
      root = {
        id: conceptData.concept.uuid || `concept-${conceptData.concept.id}`,
        title: conceptData.concept.title,
        type: 'concept',
        isRoot: true,
      };
      nodeList.push(root);

      conceptData.connected_memories.forEach((mem, idx) => {
        const targetNode: GraphNode = {
          id: mem.uuid || `mem-${idx}`,
          title: mem.title,
          type: (mem as any).type || mem.object_type || 'memory',
          source: (mem as any).source || mem.source_system,
        };
        nodeList.push(targetNode);
        edgeList.push({
          id: `edge-concept-${idx}`,
          sourceId: root!.id,
          targetId: targetNode.id,
          label: 'connected_memory',
          confidence: 0.95,
        });
      });
    } 
    // SCENARIO B: Backend Object Detail response available
    else if (objectData) {
      root = {
        id: objectData.uuid,
        title: objectData.title,
        type: objectData.type,
        source: objectData.source,
        isRoot: true,
      };
      nodeList.push(root);

      // Add connected concepts
      objectData.connected_concepts?.forEach((cc, idx) => {
        const cNode: GraphNode = {
          id: cc.uuid || `cc-${idx}`,
          title: cc.title,
          type: 'concept',
        };
        nodeList.push(cNode);
        edgeList.push({
          id: `edge-cc-${idx}`,
          sourceId: root!.id,
          targetId: cNode.id,
          label: 'linked_concept',
          confidence: 0.9,
        });
      });

      // Add explicit relationships
      objectData.relationships?.forEach((rel, idx) => {
        const relNode: GraphNode = {
          id: rel.target_object_uuid,
          title: rel.target_object_title,
          type: rel.target_object_type,
        };
        nodeList.push(relNode);
        edgeList.push({
          id: `edge-rel-${idx}`,
          sourceId: root!.id,
          targetId: relNode.id,
          label: rel.relationship_type,
          confidence: rel.confidence,
        });
      });
    } 
    // SCENARIO C: Grounded Turn Evidence Fallback
    else if (currentMessage?.evidence && currentMessage.evidence.length > 0) {
      root = {
        id: currentMessage.uuid,
        title: activeConceptName || (currentMessage.content.length > 40 ? currentMessage.content.slice(0, 36) + '...' : currentMessage.content),
        type: activeConceptName ? 'concept' : 'dialogue_turn',
        isRoot: true,
      };
      nodeList.push(root);

      currentMessage.evidence.forEach((ev, idx) => {
        const path = ev.relationship_path || [];
        const label = path.join(' ➔ ') || 'associative_recall';
        const targetTitle = path[1] || (ev.reason.length > 35 ? ev.reason.slice(0, 32) + '...' : ev.reason);
        const targetType = path[0]?.toLowerCase() || 'openmemory';

        const evNode: GraphNode = {
          id: ev.source_uuid || `ev-${idx}`,
          title: targetTitle,
          type: targetType,
          metadata: ev.reason,
        };
        nodeList.push(evNode);
        edgeList.push({
          id: `edge-ev-${idx}`,
          sourceId: root!.id,
          targetId: evNode.id,
          label: label,
          confidence: ev.confidence ?? 0.85,
          reason: ev.reason,
        });
      });
    }

    return { nodes: nodeList, edges: edgeList, rootNode: root };
  }, [conceptData, objectData, currentMessage, activeConceptName, activeEvidenceId]);

  const renderNodeIcon = (type: string) => {
    switch (type.toLowerCase()) {
      case 'concept':
        return <Brain className="w-3.5 h-3.5 text-purple-400" />;
      case 'openmemory':
        return <Database className="w-3.5 h-3.5 text-blue-400" />;
      case 'note':
      case 'memory':
        return <FileText className="w-3.5 h-3.5 text-emerald-400" />;
      case 'dialogue_turn':
        return <Sparkles className="w-3.5 h-3.5 text-indigo-400" />;
      default:
        return <Network className="w-3.5 h-3.5 text-accent-assistant" />;
    }
  };

  const getConfidenceStyle = (confidence: number) => {
    if (confidence >= 0.85) {
      return {
        lineColor: 'stroke-emerald-400/70',
        badgeBg: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/25',
        border: 'border-emerald-500/30',
        strokeWidth: 2.5,
      };
    }
    if (confidence >= 0.65) {
      return {
        lineColor: 'stroke-amber-400/70',
        badgeBg: 'bg-amber-500/10 text-amber-400 border-amber-500/25',
        border: 'border-amber-500/30',
        strokeWidth: 2,
      };
    }
    return {
      lineColor: 'stroke-indigo-400/60',
      badgeBg: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/25',
      border: 'border-indigo-500/30',
      strokeWidth: 1.5,
    };
  };

  return (
    <div className="space-y-3 select-none">
      {/* Entity Context Navigation Strip */}
      <div className="p-2.5 rounded-xl border border-border-primary/70 bg-background-primary/30 flex items-center justify-between gap-2">
        <div className="flex items-center space-x-1.5 min-w-0">
          <Share2 className="w-3.5 h-3.5 text-purple-400 shrink-0" />
          <span className="text-[10px] font-bold text-text-primary truncate">
            {rootNode ? rootNode.title : 'Graph View'}
          </span>
          {activeEvidenceId && (
            <button
              onClick={() => {
                setActiveEvidenceId(null);
                setActiveConceptName(null);
                setActiveObjectUuid(null);
              }}
              className="flex items-center space-x-1 px-1.5 py-0.5 rounded text-[8.5px] font-bold text-accent-assistant bg-accent-assistant/10 hover:bg-accent-assistant/20 cursor-pointer transition-colors shrink-0"
              title="Reset graph view to dialogue turn"
            >
              <RotateCcw className="w-2.5 h-2.5" />
              <span>Reset to Turn</span>
            </button>
          )}
        </div>

        {/* Entity Switcher Pills if concepts exist */}
        {conceptsList.length > 0 && (
          <select
            value={activeConceptName || ''}
            onChange={(e) => {
              if (e.target.value) {
                setActiveConceptName(e.target.value);
                setActiveObjectUuid(null);
                setActiveEvidenceId(null);
              }
            }}
            className="text-[9px] font-semibold bg-surface-card border border-border-primary rounded-lg px-2 py-1 text-text-secondary focus:outline-none focus:border-accent-assistant max-w-[130px] truncate cursor-pointer"
          >
            <option value="">Switch Concept...</option>
            {conceptsList.map((c) => (
              <option key={c.concept.id} value={c.concept.title}>
                {c.concept.title}
              </option>
            ))}
          </select>
        )}

        <div className="flex items-center space-x-1 text-[8.5px] font-bold shrink-0 text-text-secondary">
          <span className="px-1.5 py-0.5 rounded bg-surface-card border border-border-primary/60">
            {nodes.length} Nodes
          </span>
          <span className="px-1.5 py-0.5 rounded bg-surface-card border border-border-primary/60">
            {edges.length} Edges
          </span>
        </div>
      </div>

      {loading && (
        <div className="py-12 flex flex-col items-center justify-center space-y-2 animate-pulse">
          <Network className="w-6 h-6 text-purple-400 animate-spin" />
          <span className="text-[10px] text-text-secondary font-medium">Resolving graph topology...</span>
        </div>
      )}

      {/* Node-Link Visual Graph Representation */}
      {!loading && rootNode && edges.length > 0 && (
        <div className="p-3 rounded-2xl border border-border-primary/80 bg-surface-card/40 space-y-4">
          {/* ROOT FOCUS NODE */}
          <div className="flex flex-col items-center">
            <div className="px-4 py-2.5 rounded-xl border-2 border-accent-assistant/50 bg-accent-assistant/10 shadow-md flex items-center space-x-2.5 max-w-full">
              <div className="p-1 rounded-lg bg-surface-card/80 shrink-0">
                {renderNodeIcon(rootNode.type)}
              </div>
              <div className="min-w-0">
                <span className="font-extrabold text-[11px] text-text-primary tracking-tight block truncate">
                  {rootNode.title}
                </span>
                <span className="text-[8px] font-mono text-accent-assistant uppercase tracking-wider">
                  Root {rootNode.type}
                </span>
              </div>
            </div>

            {/* Central Vertical Trunk Line */}
            <div className="w-0.5 h-5 bg-border-primary/80 my-0.5" />
          </div>

          {/* CONNECTED NODES & LABELED EDGES */}
          <div className="relative pl-4 space-y-3.5 border-l-2 border-border-primary/70 ml-4">
            {edges.map((edge) => {
              const targetNode = nodes.find((n) => n.id === edge.targetId);
              if (!targetNode) return null;

              const style = getConfidenceStyle(edge.confidence);

              return (
                <div key={edge.id} className="relative group">
                  {/* Horizontal Connecting Branch Line */}
                  <div className="absolute top-4 -left-4 w-4 h-0.5 bg-border-primary/70 -translate-y-1/2" />

                  {/* Node & Edge Card */}
                  <div className="space-y-1.5">
                    {/* Edge Label & Confidence Badge */}
                    <div className="flex items-center space-x-1.5 text-[8.5px] font-mono pl-1">
                      <span className={`px-1.5 py-0.5 rounded-full border font-bold uppercase tracking-wider ${style.badgeBg}`}>
                        {edge.label}
                      </span>
                      <span className="text-text-secondary/70">
                        {(edge.confidence * 100).toFixed(0)}% match
                      </span>
                    </div>

                    {/* Connected Node Pill */}
                    <div 
                      onClick={() => {
                        if (targetNode.type === 'dialogue_turn') {
                          // Return to dialogue turn root
                          setActiveEvidenceId(null);
                          setActiveConceptName(null);
                          setActiveObjectUuid(null);
                        } else if (targetNode.type === 'concept') {
                          setActiveConceptName(targetNode.title);
                          setActiveObjectUuid(null);
                          setActiveEvidenceId(null);
                        } else if (targetNode.type === 'openmemory' || targetNode.id.startsWith('ev-') || targetNode.id.startsWith('om-')) {
                          // OpenMemory / Turn evidence re-rooting using in-hand evidence
                          setActiveEvidenceId(targetNode.id);
                          setActiveConceptName(null);
                          setActiveObjectUuid(null);
                        } else if (targetNode.id.length > 20 && targetNode.type !== 'openmemory') {
                          // DeepCore SQLite registry entity lookup
                          setActiveObjectUuid(targetNode.id);
                          setActiveConceptName(null);
                          setActiveEvidenceId(null);
                        } else {
                          // Fallback for in-hand evidence node
                          setActiveEvidenceId(targetNode.id);
                          setActiveConceptName(null);
                          setActiveObjectUuid(null);
                        }
                      }}
                      className={`p-2.5 rounded-xl border bg-surface-card/70 hover:bg-background-primary/60 transition-all flex items-start justify-between gap-2 shadow-xs cursor-pointer ${style.border}`}
                    >
                      <div className="flex items-start space-x-2 min-w-0">
                        <div className="p-1 rounded-lg bg-background-primary shrink-0 mt-0.5">
                          {renderNodeIcon(targetNode.type)}
                        </div>
                        <div className="space-y-0.5 min-w-0">
                          <h6 className="text-[10.5px] font-bold text-text-primary truncate">
                            {targetNode.title}
                          </h6>
                          {targetNode.metadata && (
                            <p className="text-[9.5px] text-text-secondary line-clamp-2 leading-relaxed font-medium">
                              {targetNode.metadata}
                            </p>
                          )}
                        </div>
                      </div>

                      <span className="text-[8px] font-mono px-1.5 py-0.5 rounded bg-background-primary/80 border border-border-primary/50 text-text-secondary capitalize shrink-0">
                        {targetNode.type === 'dialogue_turn' ? 'Turn Root' : targetNode.type}
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Zero State */}
      {!loading && (!rootNode || edges.length === 0) && (
        <div className="py-12 px-4 text-center space-y-2 border border-dashed border-border-primary rounded-2xl bg-surface-card/20">
          <Network className="w-8 h-8 text-text-secondary/40 mx-auto" />
          <h5 className="text-[11px] font-bold text-text-secondary">
            No Graph Topology for Current Turn
          </h5>
          <p className="text-[10px] text-text-secondary/70 max-w-[220px] mx-auto leading-relaxed">
            Select a dialogue turn with citations or select a concept from the dropdown above to inspect its relationship graph.
          </p>
        </div>
      )}
    </div>
  );
};
