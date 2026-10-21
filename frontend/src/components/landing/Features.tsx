import { ArrowUpRight, FlaskConical, Network, ShieldCheck } from 'lucide-react';
import { motion } from 'framer-motion';

const features = [
  {
    icon: FlaskConical,
    number: '01',
    title: 'Describe the target',
    text: 'Write the goal in plain language, such as a cobalt-free cathode above 250 mAh/g and under $50/kg. AURA turns it into numeric limits and a material class.',
  },
  {
    icon: Network,
    number: '02',
    title: 'Literature linked to rules',
    text: 'Abstracts from arXiv, Crossref, PubMed and Wikipedia are filtered for relevance, de-duplicated, and mined into a knowledge graph of elements, properties and degradation modes.',
  },
  {
    icon: ShieldCheck,
    number: '03',
    title: 'Results you can check',
    text: 'Each candidate shows predicted capacity, voltage, cycle life and cost, a comparison with NMC811, and the reasoning behind the numbers.',
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
          <span className="section-kicker">What it does</span>
          <h2>Battery papers are everywhere.<br />A checkable answer is <em>rare.</em></h2>
        </div>
        <p>AURA reads the literature, links it to chemistry rules, and uses both to answer questions and to search for new materials.</p>
      </div>

      <div className="evidence-banner">
        <div className="evidence-banner__content">
          <span className="section-kicker">Built on evidence</span>
          <h3>The search stays inside chemistry rules.</h3>
          <p>The genetic algorithm keeps lithium and oxygen fixed, keeps metal fractions summing to one, and never uses an excluded element. The language model estimates properties. It does not invent compositions.</p>
          <a href="#workflow" className="text-link">See how it works <ArrowUpRight size={16} /></a>
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
