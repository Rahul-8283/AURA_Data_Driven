import { ArrowUpRight, FlaskConical, Network, ShieldCheck } from 'lucide-react';
import { motion } from 'framer-motion';

const features = [
  {
    icon: FlaskConical,
    number: '01',
    title: 'Chemistry-native exploration',
    text: 'Start with a real battery question. AURA understands cathodes, anodes, electrolytes, doping, and the trade-offs that define each.',
  },
  {
    icon: Network,
    number: '02',
    title: 'A connected evidence field',
    text: 'Literature, material relationships, degradation modes, and synthesis constraints stay connected instead of becoming another pile of PDFs.',
  },
  {
    icon: ShieldCheck,
    number: '03',
    title: 'Recommendations you can defend',
    text: 'Every promising candidate is ranked with predicted properties, confidence, and the exact reasoning your research team can inspect.',
  },
];

const Features = () => (
  <motion.section 
    id="intelligence" 
    className="intelligence-section section-space"
    initial={{ opacity: 0, y: 30 }}
    whileInView={{ opacity: 1, y: 0 }}
    viewport={{ once: true, margin: "-100px" }}
    transition={{ duration: 0.6 }}
  >
    <div className="site-frame">
      <div className="section-heading section-heading--split">
        <div>
          <span className="section-kicker">Designed for scientific taste</span>
          <h2>Research has never been short on data.<br />It has been short on <em>clarity.</em></h2>
        </div>
        <p>AURA brings the whole discovery loop into focus, so every new direction begins with more signal and less speculation.</p>
      </div>

      <div className="evidence-banner">
        <div className="evidence-banner__content">
          <span className="section-kicker">The AURA difference</span>
          <h3>Not a chatbot with chemistry vocabulary.</h3>
          <p>It is a research system that evolves possible materials, tests them against known constraints, and explains why the best ones deserve attention.</p>
          <a href="#workflow" className="text-link">Follow the discovery loop <ArrowUpRight size={16} /></a>
        </div>
        <div className="evidence-banner__visual" aria-hidden="true">
          <span className="evidence-orbit evidence-orbit--one" />
          <span className="evidence-orbit evidence-orbit--two" />
          <span className="evidence-node evidence-node--one">Li</span>
          <span className="evidence-node evidence-node--two">O</span>
          <span className="evidence-node evidence-node--three">Ni</span>
          <span className="evidence-node evidence-node--four">Mg</span>
          <span className="evidence-line evidence-line--one" />
          <span className="evidence-line evidence-line--two" />
          <span className="evidence-line evidence-line--three" />
        </div>
      </div>

      <div className="feature-grid">
        {features.map((feature) => {
          const Icon = feature.icon;
          return (
            <article className="feature-card" key={feature.number}>
              <div className="feature-card__top"><span>{feature.number}</span><Icon size={21} /></div>
              <h3>{feature.title}</h3>
              <p>{feature.text}</p>
              <div className="feature-card__rule" />
            </article>
          );
        })}
      </div>
    </div>
  </motion.section>
);

export default Features;
