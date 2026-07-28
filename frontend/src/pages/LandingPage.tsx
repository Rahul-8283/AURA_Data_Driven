import { useEffect } from 'react';
import Lenis from 'lenis';
import 'lenis/dist/lenis.css';
import { ArrowUpRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import Hero from '../components/landing/Hero';
import Features from '../components/landing/Features';
import HowItWorks from '../components/landing/HowItWorks';
import CallToAction from '../components/landing/CallToAction';
import AuraMark from '../components/shared/AuraMark';

const LandingPage = () => {
  useEffect(() => {
    const lenis = new Lenis({ autoRaf: true, smoothWheel: true });
    return () => lenis.destroy();
  }, []);

  return (
    <div className="aura-app">
      <main>
        <Hero />
        <Features />
        <HowItWorks />
        <CallToAction />
      </main>

      <footer className="site-footer">
        <div className="site-frame site-footer__inner">
          <AuraMark compact />
          <p>Autonomous Unified Research Assistant for Battery Materials Discovery.</p>
          <div className="site-footer__links">
            <a href="#intelligence">Intelligence <ArrowUpRight size={14} /></a>
            <Link to="/login">Research space <ArrowUpRight size={14} /></Link>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;
