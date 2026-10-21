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
  source_errors?: Record<string, string>;
  extraction_task_id?: string | null;
  chunks_extracted?: number | null;
  chunks_pending?: number | null;
  triplets_ingested?: number | null;
  stopped_reason?: string | null;
}

export interface KnowledgeStatsResponse {
  // null means the store could not be reached, which is not the same as empty
  chroma_literature_chunks: number | null;
  neo4j_nodes: number | null;
  neo4j_relationships: number | null;
  errors: { chroma?: string; neo4j?: string };
  supported_sources: string[];
  nightly_sweep_enabled: boolean;
}
