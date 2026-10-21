import { useState } from 'react';
import { ArrowRight, Menu, X } from 'lucide-react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import AuraMark from '../shared/AuraMark';

const navItems = [
  { label: 'What it does', href: '#intelligence' },
  { label: 'How it works', href: '#workflow' },
  { label: 'Get started', href: '#research-notes' },
];

const Hero = () => {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
  <motion.section 
    className="hero-section"
    initial={{ opacity: 0 }}
    animate={{ opacity: 1 }}
    transition={{ duration: 0.8 }}
  >
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
            <Link to="/login" onClick={() => setMenuOpen(false)}>Enter AURA</Link>
          </nav>
        )}

        <div className="hero-grid">
          <div className="hero-copy">
            <div className="eyebrow">Battery materials research</div>
            <h1>Find the next battery material, <em>with the evidence</em> attached.</h1>
            <p className="hero-copy__lede">
              Ask a question and get an answer drawn from battery papers, with every source cited. Or describe a
              target and let AURA evolve and rank new cathode compositions, checked against literature and chemistry rules.
            </p>

            <div className="hero-actions">
              <Link to="/login" className="button button--primary">Start a discovery <ArrowRight size={17} /></Link>
              <a href="#workflow" className="button button--ghost">How it works</a>
            </div>

            <div className="hero-proof">
              <div className="hero-proof__avatars" aria-hidden="true">
                <span>Li</span><span>Ni</span><span>Mn</span><span>Ti</span>
              </div>
              <p><strong>Two modes, one evidence base.</strong> Ask cites its sources. Discover shows why each candidate ranks.</p>
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
                <span><i /> Example discovery run</span>
                <span>5 GENERATIONS</span>
              </div>

              <div className="material-console__core">
                <span className="material-console__label">Top-ranked candidate</span>
                <div className="material-formula">LiAl<sub>0.068</sub>Mn<sub>0.109</sub>Ni<sub>0.8</sub>Ti<sub>0.023</sub>O<sub>2</sub></div>
                <p>Cobalt-free layered cathode, scored against the NMC811 baseline</p>
              </div>

              <div className="material-console__signal-grid">
                <div><span>Capacity</span><strong>205 <small>mAh/g</small></strong></div>
                <div><span>Cycle life</span><strong>2,200 <small>cycles</small></strong></div>
                <div><span>Cost</span><strong>$28.5 <small>/kg</small></strong></div>
              </div>

              <div className="material-console__trail" aria-hidden="true">
                <span className="trail-dot trail-dot--one" />
                <span className="trail-dot trail-dot--two" />
                <span className="trail-dot trail-dot--three" />
                <span className="trail-dot trail-dot--four" />
              </div>
            </div>

            <div className="hero-insight-card">
              <span className="hero-insight-card__eyebrow">Ask mode</span>
              <p>Answers cite the papers and graph rules they use, and say so when evidence is missing.</p>
              <span className="hero-insight-card__source">Cited sources [S1] [S2]</span>
            </div>
          </div>
        </div>

        <div className="hero-marquee" aria-label="AURA capabilities">
          <span>arXiv and Crossref</span><i />
          <span>PubMed and Wikipedia</span><i />
          <span>Knowledge-graph rules</span><i />
          <span>PDF reports</span>
        </div>
      </div>
    </motion.section>
  );
};

export default Hero;
