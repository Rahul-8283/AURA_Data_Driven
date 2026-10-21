import { ArrowRight, Check } from 'lucide-react';
import { motion } from 'framer-motion';

const steps = [
  { number: '01', name: 'Frame the question', detail: 'Set the component, the performance target, the cost ceiling and any elements to exclude, in plain language.' },
  { number: '02', name: 'Grow the possibility space', detail: 'Start from known materials, then dope, substitute and recombine them over several generations.' },
  { number: '03', name: 'Filter with evidence', detail: 'Each new composition is validated against the knowledge graph, and its prediction uses literature context.' },
  { number: '04', name: 'Choose what earns a synthesis', detail: 'Review ranked candidates with predicted properties, scores and a PDF report you can share with your team.' },
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
        <span className="section-kicker">How it works</span>
        <h2>From a target to a<br /><em>ranked shortlist.</em></h2>
        <p>Every step leaves a trace, so you can check why a composition made the list before it is worth lab time.</p>
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
          <span className="workflow-aside__eyebrow">Per run</span>
          <div className="workflow-aside__metric"><strong>42</strong><span>LLM requests in a<br />full discovery run</span></div>
          <ul>
            <li><Check size={14} /> Excluded elements never enter a candidate</li>
            <li><Check size={14} /> Answers use only the retrieved context</li>
            <li><Check size={14} /> No silent zero scores when the LLM fails</li>
          </ul>
          <span className="workflow-aside__glow" aria-hidden="true" />
        </aside>
      </div>
    </div>
  </motion.section>
);

export default HowItWorks;
