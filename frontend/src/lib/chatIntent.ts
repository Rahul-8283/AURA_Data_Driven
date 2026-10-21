import type { ChatMode } from '../types/chat';

const COMMAND = /^\/(ask|discover)\b\s*/i;

const QUESTION_START =
  /^(what|which|how|why|when|where|who|does|do|is|are|can|could|should|explain|compare|describe|summari[sz]e|tell me|list)\b/i;
const DESIGN_VERB =
  /\b(find|design|discover|explore|propose|suggest|generate|create|optimi[sz]e|develop|identify|evolve)\b/i;
const NUMERIC_TARGET =
  /(>=|<=|>|<|≥|≤|\babove\b|\bbelow\b|\bover\b|\bunder\b|\bat least\b|\bat most\b|\bmore than\b|\bless than\b)\s*\$?\d/i;

/** `/ask ...` or `/discover ...` forces the mode for one message and is stripped from the text. */
export function parseCommand(input: string): { mode: ChatMode | null; text: string } {
  const trimmed = input.trim();
  const match = COMMAND.exec(trimmed);
  if (!match) return { mode: null, text: trimmed };
  return { mode: match[1].toLowerCase() as ChatMode, text: trimmed.slice(match[0].length).trim() };
}

/**
 * A hint about which mode a message fits, or null when it is neutral or could be either. The chat
 * only uses it to ask before sending, never to choose silently.
 */
export function suggestMode(text: string): ChatMode | null {
  const trimmed = text.trim();
  const questionLike = QUESTION_START.test(trimmed) || trimmed.endsWith('?');
  const designLike = DESIGN_VERB.test(trimmed) || NUMERIC_TARGET.test(trimmed);
  if (designLike && !questionLike) return 'discover';
  if (questionLike && !designLike) return 'ask';
  return null;
}
