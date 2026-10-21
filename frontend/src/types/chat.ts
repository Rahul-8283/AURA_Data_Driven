export type ChatMode = 'ask' | 'discover';

export interface AskSource {
  id: string;
  title: string;
  doi: string | null;
  url: string | null;
  source: string | null;
  snippet: string;
  distance: number;
}

export interface AskResponse {
  answer: string;
  grounded: boolean;
  sources: AskSource[];
  graph_rules: string[];
  remaining_today: number | null;
}
