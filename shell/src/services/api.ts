export interface RegistryObject {
  id: number;
  uuid: string;
  object_type: string;
  title: string;
  source_system: string;
  external_id?: string;
  location?: string;
  description?: string;
  status: string;
  metadata_json?: string;
  provider_version?: string;
  content_hash?: string;
  created_at: string;
  updated_at: string;
}

export interface SidebarSourceEntry {
  id: string;
  name: string;
  count: number;
  visible: boolean;
}

export interface SystemStats {
  total_objects: number;
  by_type: Record<string, number>;
  by_source: Record<string, number>;
  concept_count: number;
  relationship_count: number;
  sources: SidebarSourceEntry[];
}

export interface ContentIndex {
  id: number;
  uuid: string;
  object_id: number;
  content_type: string;
  raw_text: string;
  content_hash: string;
  word_count: number;
  index_version: string;
  indexed_at: string;
}

export interface ConceptListEntry {
  concept: RegistryObject;
  connection_count: number;
}

export interface CognitiveFocus {
  title: string;
  object_type: string;
  object_uuid: string;
  description: string;
  last_accessed: string;
}

export interface SemanticChange {
  title: string;
  change_type: string;
  description: string;
  time_ago: string;
  object_uuid?: string;
}

export interface CognitiveObservation {
  id: string;
  observation_type: string;
  title: string;
  description: string;
  severity: string;
  action_label: string;
  action_route: string;
}

export interface CognitiveNextStep {
  title: string;
  prompt: string;
  action_label: string;
}

export interface CapabilitySummary {
  id: string;
  name: string;
  description: string;
  category: string;
  enabled: boolean;
  configurable: boolean;
  experimental: boolean;
  tags: string[];
  metadata: Record<string, any>;
  icon?: string;
  accent_color?: string;
  availability_state?: 'available' | 'coming_soon' | 'disabled' | string;
}

export interface ThinkingModeDescriptor {
  id: string;
  name: string;
  description: string;
  icon: string;
}

export interface Evidence {
  source_uuid: string;
  target_uuid: string;
  relationship_path: string[];
  reason: string;
  confidence?: number;
}

export interface Message {
  uuid: string;
  role: 'user' | 'assistant';
  content: string;
  evidence?: Evidence[];
  created_at: string;
}

export interface ConversationState {
  session_uuid: string;
  conversation_uuid: string;
  active_thinking_mode: string;
  focus_intent: CognitiveFocus[];
  awareness: {
    summary: DashboardSummary;
    observations: CognitiveObservation[];
  };
  context_package: {
    focus_count: number;
    observations_count: number;
    timestamp: string;
  };
  title: string;
  messages: Message[];
  created_at: string;
  updated_at: string;
}

export interface DashboardSummary {
  memory_count: number;
  concept_count: number;
  relationship_count: number;
}

export interface DashboardResponse {
  summary: DashboardSummary;
  focus: CognitiveFocus[];
  orientation: SemanticChange[];
  understanding: CognitiveObservation[];
  continuation: CognitiveNextStep[];
}

export interface ContentSearchResult {
  object: RegistryObject;
  content: ContentIndex;
}

export interface ConceptShort {
  id: number;
  uuid: string;
  title: string;
}

export interface ReferencedObjectShort {
  id: number;
  uuid: string;
  title: string;
  object_type: string;
  location?: string;
}

export interface RelationshipDetailResponse {
  uuid: string;
  target_object_uuid: string;
  target_object_title: string;
  target_object_type: string;
  relationship_type: string;
  confidence: number;
  evidence?: any;
  created_at: string;
  updated_at: string;
  navigation_hint?: string;
}

export interface SignalDetailResponse {
  uuid: string;
  signal_type: string;
  value?: string;
  confidence: number;
  generated_by: string;
  evidence?: any;
  created_at: string;
  updated_at: string;
}

export interface ObjectDetailsResponse {
  uuid: string;
  type: string;
  title: string;
  source: string;
  location?: string;
  status: string;
  metadata_json?: string;
  created_at: string;
  updated_at: string;
  connected_concepts: ConceptShort[];
  referenced_objects?: ReferencedObjectShort[];
  relationships?: RelationshipDetailResponse[];
  signals?: SignalDetailResponse[];
}

export interface ConceptDetailResponse {
  concept: RegistryObject;
  connected_memories: RegistryObject[];
}

export interface Workspace {
  id: number;
  uuid: string;
  name: string;
  created_at: string;
  updated_at: string;
}

export interface KnowledgeSource {
  id: number;
  uuid: string;
  workspace_id: number;
  provider_id: string;
  kind: string;
  name: string;
  location: string;
  config_json?: string;
  created_at: string;
  updated_at: string;
}

export interface WorkspaceSourceInfo {
  uuid: string;
  name: string;
  kind: string;
  provider_id: string;
  location: string;
  config_json?: string;
}

export interface WorkspaceDiagnostics {
  workspace_id: number;
  workspace_uuid: string;
  workspace_name: string;
  db_path: string;
  object_count: number;
  relationship_count: number;
  signal_count: number;
  last_sync_run?: any;
  registered_providers: string[];
  registered_sources: WorkspaceSourceInfo[];
  active_stages: any[];
}

// Custom error class to carry API error messages
export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
    this.name = 'ApiError';
  }
}

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const activeWorkspaceUuid = localStorage.getItem('activeWorkspaceUuid');
  const newOptions: RequestInit = { ...(options || {}) };
  
  if (activeWorkspaceUuid) {
    const headers = new Headers(newOptions.headers || {});
    headers.set('X-Workspace-UUID', activeWorkspaceUuid);
    newOptions.headers = headers;
  }

  const response = await fetch(url, newOptions);
  if (!response.ok) {
    let errorMessage = `HTTP error! status: ${response.status}`;
    try {
      const errBody = await response.json();
      if (errBody && errBody.detail) {
        errorMessage = errBody.detail;
      }
    } catch {
      // Fall back to default message if JSON parsing fails
    }
    throw new ApiError(errorMessage, response.status);
  }
  return response.json() as Promise<T>;
}

export const api = {
  async getDashboard(): Promise<DashboardResponse> {
    return fetchJson<DashboardResponse>('/api/dashboard');
  },

  async getRecentMemories(limit = 10): Promise<RegistryObject[]> {
    return fetchJson<RegistryObject[]>(`/api/memories/recent?limit=${limit}`);
  },

  async getConcepts(limit = 50, showIgnored = false): Promise<ConceptListEntry[]> {
    return fetchJson<ConceptListEntry[]>(`/api/concepts?limit=${limit}&show_ignored=${showIgnored}`);
  },

  async searchContent(query: string): Promise<ContentSearchResult[]> {
    return fetchJson<ContentSearchResult[]>(`/api/content/search?query=${encodeURIComponent(query)}`);
  },

  async getMemoryDetails(uuid: string): Promise<ObjectDetailsResponse> {
    return fetchJson<ObjectDetailsResponse>(`/api/objects/${uuid}`);
  },

  async getConceptDetails(name: string): Promise<ConceptDetailResponse> {
    return fetchJson<ConceptDetailResponse>(`/api/concepts/${encodeURIComponent(name)}`);
  },

  async getMemoryContent(uuid: string): Promise<ContentIndex> {
    return fetchJson<ContentIndex>(`/api/content/${uuid}`);
  },

  async searchObjects(query?: string, type?: string, limit = 100): Promise<RegistryObject[]> {
    const params = new URLSearchParams();
    if (query) params.append('search', query);
    if (type && type !== 'all') params.append('type', type);
    params.append('limit', limit.toString());
    return fetchJson<RegistryObject[]>(`/api/objects?${params.toString()}`);
  },

  async getStats(): Promise<SystemStats> {
    return fetchJson<SystemStats>('/api/stats');
  },

  async syncProvider(provider: string, path: string): Promise<any> {
    return fetchJson<any>(`/api/providers/${provider}/sync`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ path }),
    });
  },

  async listWorkspaces(): Promise<Workspace[]> {
    return fetchJson<Workspace[]>('/api/workspaces');
  },

  async createWorkspace(name: string): Promise<Workspace> {
    return fetchJson<Workspace>('/api/workspaces', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name }),
    });
  },

  async listWorkspaceSources(workspaceUuid: string): Promise<KnowledgeSource[]> {
    return fetchJson<KnowledgeSource[]>(`/api/workspaces/${workspaceUuid}/sources`);
  },

  async createWorkspaceSource(
    workspaceUuid: string,
    source: { provider_id: string; kind: string; name: string; location: string; config_json?: string }
  ): Promise<KnowledgeSource> {
    return fetchJson<KnowledgeSource>(`/api/workspaces/${workspaceUuid}/sources`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(source),
    });
  },

  async capture(content: string): Promise<RegistryObject> {
    return fetchJson<RegistryObject>('/api/capture', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content }),
    });
  },

  async syncSource(sourceUuid: string): Promise<any> {
    return fetchJson<any>(`/api/sources/${sourceUuid}/sync`, {
      method: 'POST',
    });
  },

  async getThinkingModes(): Promise<ThinkingModeDescriptor[]> {
    return fetchJson<ThinkingModeDescriptor[]>('/api/conversations/modes');
  },

  async startThinkingSession(thinkingMode: string, activeObjectUuid?: string): Promise<ConversationState> {
    return fetchJson<ConversationState>('/api/conversations/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ thinking_mode: thinkingMode, active_object_uuid: activeObjectUuid }),
    });
  },

  async continueConversation(sessionUuid: string, content: string): Promise<ConversationState> {
    return fetchJson<ConversationState>(`/api/conversations/${sessionUuid}/messages`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content }),
    });
  },

  async restoreConversation(sessionUuid: string): Promise<ConversationState> {
    return fetchJson<ConversationState>(`/api/conversations/${sessionUuid}`);
  },

  async postConversationAudio(sessionUuid: string, audioBlob: Blob): Promise<{ audioBlob: Blob; transcript: string }> {
    const formData = new FormData();
    const ext = audioBlob.type.includes('webm') ? 'webm' : 'wav';
    formData.append('file', audioBlob, `recording.${ext}`);

    const res = await fetch(`/api/conversations/${sessionUuid}/audio`, {
      method: 'POST',
      body: formData,
    });

    if (!res.ok) {
      const errText = await res.text();
      throw new Error(`Audio processing failed (${res.status}): ${errText}`);
    }

    const transcriptHeader = res.headers.get('X-User-Transcript');
    const transcript = transcriptHeader ? decodeURIComponent(transcriptHeader) : '';
    const blob = await res.blob();

    return { audioBlob: blob, transcript };
  },

  async getWorkspaceDiagnostics(): Promise<WorkspaceDiagnostics> {
    return fetchJson<WorkspaceDiagnostics>('/api/system/workspace');
  },

  async getSyncRuns(): Promise<SyncRun[]> {
    return fetchJson<SyncRun[]>('/api/system/runs');
  },

  async getPlatformHealth(): Promise<PlatformHealth> {
    return fetchJson<PlatformHealth>('/api/system/health');
  },

  async getObservability(): Promise<SystemObservabilityResponse> {
    return fetchJson<SystemObservabilityResponse>('/api/system/observability');
  },

  async getConnectors(): Promise<ConnectorInfo[]> {
    return fetchJson<ConnectorInfo[]>('/api/connectors');
  },

  async getProviderCapabilities(): Promise<CapabilitySummary[]> {
    return fetchJson<CapabilitySummary[]>('/api/capabilities/category/provider');
  },

  async previewConnector(providerId: string, location: string, config?: Record<string, any>): Promise<PreviewResponse> {
    return fetchJson<PreviewResponse>('/api/connectors/preview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ provider_id: providerId, location, config }),
    });
  },

  async triggerConnectorSync(providerId: string, location: string, sourceId?: number): Promise<SyncStatus> {
    return fetchJson<SyncStatus>('/api/connectors/sync', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ provider_id: providerId, location, source_id: sourceId }),
    });
  },

  async cancelConnectorSync(runUuid: string): Promise<SyncStatus> {
    return fetchJson<SyncStatus>(`/api/connectors/sync/${runUuid}/cancel`, {
      method: 'POST',
    });
  },

  async getConnectorSyncStatus(runUuid: string): Promise<SyncStatus> {
    return fetchJson<SyncStatus>(`/api/connectors/sync/status/${runUuid}`);
  },

  async disconnectConnector(sourceId: number, option: 'purge' | 'freeze'): Promise<{ status: string; message: string }> {
    return fetchJson<{ status: string; message: string }>('/api/connectors/disconnect', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ source_id: sourceId, option }),
    });
  }
};

export interface SyncRun {
  id: number;
  uuid: string;
  provider: string;
  source_location?: string;
  started_at: string;
  finished_at?: string;
  status: string;
  objects_scanned: number;
  objects_created: number;
  objects_existing: number;
  objects_updated: number;
  objects_missing: number;
  errors_json?: string;
}

export interface SubsystemHealth {
  status: 'healthy' | 'degraded' | 'unhealthy';
  message?: string;
  metrics: Record<string, any>;
}

export interface PlatformHealth {
  status: 'healthy' | 'degraded' | 'unhealthy';
  subsystems: Record<string, SubsystemHealth>;
}

export interface TimelineStage {
  id: string;
  name: string;
  status: string;
  started_at?: string;
  completed_at?: string;
  duration_ms: number;
  warnings: string[];
  errors: string[];
}

export interface ObservabilityTimeline {
  workspace_uuid: string;
  run_uuid?: string;
  status: string;
  stages: TimelineStage[];
}

export interface DescriptorEntry {
  id: string;
  name: string;
  category: string;
  version: string;
  implementation_version: string;
  configurable: boolean;
  tags: string[];
}

export interface RuntimeEntry {
  name: string;
  version: string;
  initialized: boolean;
  enabled: boolean;
  health: string;
  dependencies: string[];
  capabilities: string[];
  registration_status: string;
}

export interface ActiveExecution {
  uuid: string;
  provider: string;
  source_location: string;
  started_at: string;
}

export interface SyncRunHistoryEntry {
  uuid: string;
  provider: string;
  source_location: string;
  started_at: string;
  completed_at?: string;
  status: string;
  objects_scanned: number;
  objects_created: number;
  objects_existing: number;
  objects_updated: number;
  objects_missing: number;
  errors: string[];
}

export interface SystemObservabilityResponse {
  registered_runtimes: RuntimeEntry[];
  capability_registry: DescriptorEntry[];
  descriptor_registry: DescriptorEntry[];
  active_execution?: ActiveExecution;
  execution_queue: ActiveExecution[];
  execution_history: SyncRunHistoryEntry[];
  timeline?: ObservabilityTimeline;
}

export interface PreviewArtifact {
  name: string;
  type: 'document' | 'event' | 'video' | 'repository' | 'note' | 'transaction' | 'merchant' | 'idea' | 'concept';
  location_descriptor: string;
  size_bytes?: number;
}

export interface PreviewResponse {
  total_artifacts: number;
  preview: PreviewArtifact[];
}

export interface SyncStatus {
  run_id: string;
  state: 'running' | 'completed' | 'failed' | 'cancelled' | 'paused';
  processed: number;
  total: number;
  progress: number;
  current_artifact?: string;
  started_at: string;
  updated_at: string;
  warnings: string[];
  errors: string[];
}

export interface ConnectorInfo {
  id: number;
  uuid: string;
  provider_id: string;
  kind: string;
  name: string;
  location: string;
  status: string;
  created_at: string;
  updated_at: string;
  last_sync_time?: string;
  last_sync_status?: string;
  last_run_uuid?: string;
}


