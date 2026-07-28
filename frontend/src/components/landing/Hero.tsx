import { useState } from 'react';
import { ArrowRight, Menu, Sparkles, X } from 'lucide-react';
import { Link } from 'react-router-dom';
import AuraMark from '../shared/AuraMark';

const navItems = [
  { label: 'Intelligence', href: '#intelligence' },
  { label: 'Workflow', href: '#workflow' },
  { label: 'Research notes', href: '#research-notes' },
];

const Hero = () => {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <section className="hero-section">
      <div className="hero-aurora hero-aurora--one" />
      <div className="hero-aurora hero-aurora--two" />
      <div className="hero-noise" />

      <div className="site-frame">
        <header className="site-nav">
          <Link to="/" aria-label="AURA home" className="site-nav__brand">
            <AuraMark />
          </Link>

          <nav className="site-nav__links" aria-label="Primary navigation">
            {navItems.map((item) => (
              <a key={item.href} href={item.href}>{item.label}</a>
            ))}
          </nav>

          <Link to="/login" className="nav-login-link">Research space <ArrowRight size={15} /></Link>

          <button
            type="button"
            className="nav-menu-button"
            aria-label={menuOpen ? 'Close navigation' : 'Open navigation'}
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen((isOpen) => !isOpen)}
          >
            {menuOpen ? <X size={19} /> : <Menu size={19} />}
          </button>
        </header>

        {menuOpen && (
          <nav className="mobile-nav" aria-label="Mobile navigation">
            {navItems.map((item) => (
              <a key={item.href} href={item.href} onClick={() => setMenuOpen(false)}>{item.label}</a>
            ))}
            <Link to="/login" onClick={() => setMenuOpen(false)}>Enter research space</Link>
          </nav>
        )}

        <div className="hero-grid">
          <div className="hero-copy">
            <div className="eyebrow"><Sparkles size={14} /> Autonomous materials discovery</div>
            <h1>Make the next <em>breakthrough</em> feel inevitable.</h1>
            <p className="hero-copy__lede">
              AURA turns battery-material research into a living field of possibilities—grounded in literature,
              shaped by chemistry, and focused on what is worth making next.
            </p>

            <div className="hero-actions">
              <Link to="/login" className="button button--primary">Start a discovery <ArrowRight size={17} /></Link>
              <a href="#workflow" className="button button--ghost">See the method</a>
            </div>

            <div className="hero-proof">
              <div className="hero-proof__avatars" aria-hidden="true">
                <span>Li</span><span>Ni</span><span>Mn</span><span>Co</span>
              </div>
              <p><strong>Built for the laboratory.</strong> Traceable reasoning from question to candidate.</p>
            </div>
          </div>

          <div className="hero-stage" aria-label="AURA material discovery visualization">
            <div className="hero-stage__ring hero-stage__ring--outer" />
            <div className="hero-stage__ring hero-stage__ring--inner" />
            <span className="hero-stage__particle hero-stage__particle--one" />
            <span className="hero-stage__particle hero-stage__particle--two" />
            <span className="hero-stage__particle hero-stage__particle--three" />

            <div className="material-console">
              <div className="material-console__topline">
                <span><i /> Live discovery field</span>
                <span>GEN 08 / 20</span>
              </div>

              <div className="material-console__core">
                <span className="material-console__label">Highest-scoring composition</span>
                <div className="material-formula">LiNi<sub>0.82</sub>Mn<sub>0.10</sub>Co<sub>0.08</sub>O<sub>2</sub></div>
                <p>Layered nickel-rich cathode · validated against 43 research signals</p>
              </div>

              <div className="material-console__signal-grid">
                <div><span>Capacity</span><strong>224 <small>mAh/g</small></strong></div>
                <div><span>Cycle retention</span><strong>91 <small>%</small></strong></div>
                <div><span>Confidence</span><strong>0.87</strong></div>
              </div>

              <div className="material-console__trail" aria-hidden="true">
                <span className="trail-dot trail-dot--one" />
                <span className="trail-dot trail-dot--two" />
                <span className="trail-dot trail-dot--three" />
                <span className="trail-dot trail-dot--four" />
              </div>
            </div>

            <div className="hero-insight-card">
              <span className="hero-insight-card__eyebrow">AURA insight</span>
              <p>Mg doping may temper cation mixing at high voltage.</p>
              <span className="hero-insight-card__source">6 corroborating sources</span>
            </div>
          </div>
        </div>

        <div className="hero-marquee" aria-label="AURA capabilities">
          <span>Graph-grounded reasoning</span><i />
          <span>Candidate evolution</span><i />
          <span>Evidence-first predictions</span><i />
          <span>Lab-ready reports</span>
        </div>
      </div>
    </section>
  );
};

export default Hero;
