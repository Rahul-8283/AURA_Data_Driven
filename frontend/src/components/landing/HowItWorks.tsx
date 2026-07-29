import { ArrowRight, Check } from 'lucide-react';
import { motion } from 'framer-motion';

const steps = [
  { number: '01', name: 'Frame the question', detail: 'Set your battery component, target performance, cost range, and operating constraints in plain language.' },
  { number: '02', name: 'Grow the possibility space', detail: 'AURA seeds known materials, then explores substitutions, doping, and ratio changes through chemistry-aware mutations.' },
  { number: '03', name: 'Filter with evidence', detail: 'GraphRAG checks each possibility against literature, material relationships, and known structural constraints.' },
  { number: '04', name: 'Choose what earns a synthesis', detail: 'Review a ranked, explainable shortlist with predicted electrochemical properties and research provenance.' },
];

const HowItWorks = () => (
  <motion.section 
    id="workflow" 
    className="workflow-section section-space"
    initial={{ opacity: 0, y: 30 }}
    whileInView={{ opacity: 1, y: 0 }}
    viewport={{ once: true, margin: "-100px" }}
    transition={{ duration: 0.6 }}
  >
    <div className="site-frame">
      <div className="section-heading workflow-heading">
        <span className="section-kicker">A considered process</span>
        <h2>From a hunch to a<br /><em>credible direction.</em></h2>
        <p>Human curiosity starts the work. AURA makes sure the next move is informed, inspectable, and worth the lab time.</p>
      </div>

      <div className="workflow-layout">
        <div className="workflow-steps">
          {steps.map((step, index) => (
            <article className="workflow-step" key={step.number}>
              <div className="workflow-step__index"><span>{step.number}</span>{index < steps.length - 1 && <i />}</div>
              <div>
                <h3>{step.name}</h3>
                <p>{step.detail}</p>
              </div>
              <ArrowRight className="workflow-step__arrow" size={19} />
            </article>
          ))}
        </div>

        <aside className="workflow-aside">
          <span className="workflow-aside__eyebrow">Always in the loop</span>
          <div className="workflow-aside__metric"><strong>43</strong><span>evidence signals<br />on a single candidate</span></div>
          <ul>
            <li><Check size={14} /> No black-box recommendation</li>
            <li><Check size={14} /> No chemistry-free mutation</li>
            <li><Check size={14} /> No dead-end research trail</li>
          </ul>
          <span className="workflow-aside__glow" aria-hidden="true" />
        </aside>
      </div>
    </div>
  </motion.section>
);

export default HowItWorks;
