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

export interface SystemStats {
  total_objects: number;
  by_type: Record<string, number>;
  by_source: Record<string, number>;
  concept_count: number;
  relationship_count: number;
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

export interface DashboardSummary {
  memory_count: number;
  concept_count: number;
  approved_concepts: number;
  relationship_count: number;
}

export interface RecentlyConnectedEntry {
  uuid: string;
  title: string;
  object_type: string;
  total_connected: number;
  repo_connected: number;
  video_connected: number;
  doc_connected: number;
}

export interface DashboardResponse {
  summary: DashboardSummary;
  top_concepts: ConceptListEntry[];
  recent_memories: RegistryObject[];
  recently_connected: RecentlyConnectedEntry[];
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
}

export interface ConceptDetailResponse {
  concept: RegistryObject;
  connected_memories: RegistryObject[];
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
  const response = await fetch(url, options);
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
  }
};

