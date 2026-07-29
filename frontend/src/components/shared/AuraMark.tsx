type AuraMarkProps = {
  compact?: boolean;
  className?: string;
};

const AuraMark = ({ compact = false, className = '' }: AuraMarkProps) => (
  <div className={`aura-mark ${compact ? 'aura-mark--compact' : ''} ${className}`.trim()}>
    <span className="aura-mark__type">
      <span className="aura-mark__name">AURA</span>
      {!compact && <span className="aura-mark__descriptor">Materials intelligence</span>}
    </span>
  </div>
);

export default AuraMark;
