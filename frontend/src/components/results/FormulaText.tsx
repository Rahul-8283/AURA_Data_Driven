import type { ReactNode } from 'react';

const TOKEN = /([A-Z][a-z]?)(\d*\.?\d+)?/g;

// Stoichiometry is shown to three decimals; the full value stays in the tooltip.
function displayAmount(raw: string): string {
  const value = Number(raw);
  return Number.isFinite(value) ? String(Number(value.toFixed(3))) : raw;
}

export default function FormulaText({ formula }: { formula: string }) {
  const pieces: ReactNode[] = [];
  let cursor = 0;
  let key = 0;

  for (const match of formula.matchAll(TOKEN)) {
    const index = match.index ?? 0;
    if (index > cursor) pieces.push(formula.slice(cursor, index));
    pieces.push(<span key={key++}>{match[1]}</span>);
    if (match[2]) pieces.push(<sub key={key++}>{displayAmount(match[2])}</sub>);
    cursor = index + match[0].length;
  }
  if (cursor < formula.length) pieces.push(formula.slice(cursor));

  return <span title={formula}>{pieces}</span>;
}
