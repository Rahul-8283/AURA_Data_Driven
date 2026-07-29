import { ArrowRight, Sparkles } from 'lucide-react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';

const CallToAction = () => (
  <motion.section 
    id="research-notes" 
    className="cta-section section-space"
    initial={{ opacity: 0, y: 30 }}
    whileInView={{ opacity: 1, y: 0 }}
    viewport={{ once: true, margin: "-100px" }}
    transition={{ duration: 0.6 }}
  >
    <div className="site-frame">
      <div className="cta-card">
        <div className="cta-card__content">
          <span className="section-kicker"><Sparkles size={14} /> The next material is waiting</span>
          <h2>Give your best questions<br />a more powerful <em>next step.</em></h2>
          <p>Open an AURA research space and turn a battery-material requirement into a path your team can evaluate with confidence.</p>
          <Link to="/login" className="button button--light">Enter AURA <ArrowRight size={17} /></Link>
        </div>
        <div className="cta-card__annotation" aria-hidden="true">
          <span>EXPLORE</span><i /><span>VALIDATE</span><i /><span>DISCOVER</span>
        </div>
      </div>
    </div>
  </motion.section>
);

export default CallToAction;
