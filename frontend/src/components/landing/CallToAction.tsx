import { ArrowRight } from 'lucide-react';
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
          <span className="section-kicker">Get started</span>
          <h2>Ask the literature, or<br /><em>search for the next material.</em></h2>
          <p>Create an account to ask questions over the harvested papers or start a discovery run for a target you describe. Your runs and reports stay private to your account.</p>
          <Link to="/login" className="button button--light">Enter AURA <ArrowRight size={17} /></Link>
        </div>
        <div className="cta-card__annotation" aria-hidden="true">
          <span>ASK</span><i /><span>DISCOVER</span><i /><span>REPORT</span>
        </div>
      </div>
    </div>
  </motion.section>
);

export default CallToAction;
