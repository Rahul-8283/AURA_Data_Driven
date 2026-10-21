const WHOLE = new Intl.NumberFormat('en', { maximumFractionDigits: 0 });
const COMPACT = new Intl.NumberFormat('en', { notation: 'compact', maximumFractionDigits: 1 });

export const formatScore = (value: number): string => WHOLE.format(value);
export const formatCompact = (value: number): string => COMPACT.format(value);
