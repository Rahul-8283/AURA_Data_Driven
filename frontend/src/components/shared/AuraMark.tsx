type AuraMarkProps = {
  compact?: boolean;
  className?: string;
};

const AuraMark = ({ compact = false, className = '' }: AuraMarkProps) => (
  <div className={`aura-mark ${compact ? 'aura-mark--compact' : ''} ${className}`.trim()}>
    <span className="aura-mark__symbol" aria-hidden="true">
      <svg viewBox="0 0 42 42" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M21 3.75 36.8 12.9v18.2L21 40.25 5.2 31.1V12.9L21 3.75Z" stroke="currentColor" strokeWidth="1.4" />
        <path d="m21 10.5 9.96 5.75v11.5L21 33.5l-9.96-5.75v-11.5L21 10.5Z" stroke="currentColor" strokeWidth="1.1" opacity=".55" />
        <circle cx="21" cy="22" r="4.25" fill="currentColor" />
        <circle cx="30.96" cy="16.25" r="2" fill="currentColor" opacity=".72" />
      </svg>
    </span>
    <span className="aura-mark__type">
      <span className="aura-mark__name">AURA</span>
      {!compact && <span className="aura-mark__descriptor">Materials intelligence</span>}
    </span>
  </div>
);

export default AuraMark;
