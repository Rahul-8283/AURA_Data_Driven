export type IngestionSource = 'all' | 'arxiv' | 'wikipedia' | 'crossref' | 'pubmed';

export interface IngestionSyncRequest {
  query: string;
  sources: IngestionSource[];
  max_results: number;
}

export interface IngestionSyncResponse {
  task_id: string;
  status: string;
  query: string;
  sources: string[];
  message: string;
}

export interface IngestionStatusResponse {
  status: 'Pending' | 'In Progress' | 'Complete' | 'Failed';
  stage?: string;
  message?: string;
  papers_found?: number;
  new_papers_indexed?: number;
  sources?: string[];
  query?: string;
  error?: string;
}

export interface KnowledgeStatsResponse {
  chroma_literature_chunks: number;
  neo4j_nodes: number;
  neo4j_relationships: number;
  supported_sources: string[];
}
