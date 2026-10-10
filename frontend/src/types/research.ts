export interface MaterialCandidate {
  id?: string;
  composition: string;
  fitness: number;
  specific_capacity: number;
  voltage: number;
  cycle_life: number;
  cost_estimate_usd_kg: number;
  reasoning: string;
  error?: string;
}

export interface GenerationHistoryPoint {
  generation: number;
  best_score: number;
  average_score: number;
}

export interface ResearchStatusResponse {
  status: string;
  generation: number;
  best_score: number;
  results?: MaterialCandidate[];
  executive_summary?: string;
  generation_history?: GenerationHistoryPoint[];
  error?: string;
}

export interface MaterialGraphNode {
  id: string;
  label: string;
  type: 'Material' | 'Element' | 'Property' | 'DegradationMode';
}

export interface MaterialGraphLink {
  source: string;
  target: string;
  type: string;
}

export interface MaterialGraphResponse {
  nodes: MaterialGraphNode[];
  links: MaterialGraphLink[];
}
