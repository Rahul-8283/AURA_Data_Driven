import { useEffect, useRef, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Download, Loader2 } from 'lucide-react';
import { motion } from 'framer-motion';
import Lenis from 'lenis';
import api from '../lib/api';
import type { ResearchStatusResponse } from '../types/research';
import MaterialCard from '../components/results/MaterialCard';
import EvolutionChart from '../components/results/EvolutionChart';
import MaterialGraph from '../components/results/MaterialGraph';
import { exportReportPdf } from '../lib/exportReportPdf';
import { formatScore } from '../lib/format';

const fadeInUp = {
  hidden: { opacity: 0, y: 24 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5 } },
};

const Results = () => {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();
  const [status, setStatus] = useState<ResearchStatusResponse | null>(null);
  const [error, setError] = useState('');
  const [selectedMaterial, setSelectedMaterial] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);
  const reportRef = useRef<HTMLDivElement>(null);

  const handleDownloadPdf = async () => {
    if (!reportRef.current || exporting) return;
    setExporting(true);
    try {
      await exportReportPdf(reportRef.current, `AURA-Discovery-Report-${taskId}.pdf`);
    } finally {
      setExporting(false);
    }
  };

  useEffect(() => {
    const lenis = new Lenis();
    function raf(time: number) {
      lenis.raf(time);
      requestAnimationFrame(raf);
    }
    requestAnimationFrame(raf);
    return () => {
      lenis.destroy();
    };
  }, []);

  useEffect(() => {
    if (!taskId) return;
    let isMounted = true;

    const fetchStatus = async () => {
      try {
        const { data } = await api.get<ResearchStatusResponse>(`/api/v1/research/status/${taskId}`);
        if (isMounted) setStatus(data);
      } catch {
        if (isMounted) setError('Could not load this research report.');
      }
    };

    fetchStatus();
    return () => {
      isMounted = false;
    };
  }, [taskId]);

  if (error) {
    return <div className="workspace-loading">{error}</div>;
  }

  if (!status || status.status !== 'Complete') {
    return <div className="workspace-loading"><span className="workspace-loading__orb" /> Loading research report…</div>;
  }

  const candidates = status.results ?? [];
  const history = status.generation_history ?? [];
  const graphMaterial = selectedMaterial ?? candidates[0]?.composition ?? null;
  const summaryParagraphs = (status.executive_summary ?? '').split(/\n\s*\n/).filter((p) => p.trim());

  const headline = candidates.length
    ? [
        { label: 'Candidates', value: String(candidates.length) },
        { label: 'Best score', value: formatScore(Math.max(...candidates.map((c) => c.fitness))) },
        { label: 'Top capacity', value: `${Math.round(Math.max(...candidates.map((c) => c.specific_capacity)))} mAh/g` },
        { label: 'Lowest cost', value: `$${Math.min(...candidates.map((c) => c.cost_estimate_usd_kg)).toFixed(2)}/kg` },
        { label: 'Longest cycle life', value: `${formatScore(Math.max(...candidates.map((c) => c.cycle_life)))} cycles` },
        { label: 'Generations', value: String(history.length) },
      ]
    : [];

  const sectionMotion = {
    initial: 'hidden' as const,
    whileInView: 'visible' as const,
    viewport: { once: true, margin: '-80px' },
    variants: fadeInUp,
  };

  return (
    <div className="workspace-shell" style={{ gridTemplateColumns: '1fr' }}>
      <main className="workspace-main">
        <header className="workspace-header">
          <button type="button" className="workspace-header__icon" onClick={() => navigate('/dashboard/discovery')} aria-label="Back to dashboard">
            <ArrowLeft size={18} />
          </button>
          <div className="workspace-breadcrumb"><strong>Discovery report</strong></div>
          <div className="workspace-header__actions">
            <button type="button" className="results-download-btn" onClick={handleDownloadPdf} disabled={exporting}>
              {exporting ? <Loader2 size={16} className="animate-spin" /> : <Download size={16} />}
              {exporting ? 'Preparing PDF…' : 'Download PDF'}
            </button>
          </div>
        </header>

        <div className="results-page" ref={reportRef}>
          <div className="results-hero">
            <div>
              <h1>Discovery report</h1>
              <p>The top materials from this evolutionary search, with their predicted properties and the chemistry behind them.</p>
            </div>
          </div>

          {headline.length > 0 && (
            <div className="results-kpis">
              {headline.map((item) => (
                <div className="results-kpi" key={item.label}>
                  <span>{item.label}</span>
                  <strong>{item.value}</strong>
                </div>
              ))}
            </div>
          )}

          {summaryParagraphs.length > 0 && (
            <motion.section className="results-section" {...sectionMotion}>
              <h2>Summary</h2>
              <div className="results-summary">
                {summaryParagraphs.map((paragraph, index) => (
                  <p key={index}>{paragraph.trim()}</p>
                ))}
              </div>
            </motion.section>
          )}

          {history.length > 0 && (
            <motion.section className="results-section" {...sectionMotion}>
              <h2>How the search improved</h2>
              <p className="results-section__hint">Best and average score in each generation. Higher is better.</p>
              <EvolutionChart data={history} />
            </motion.section>
          )}

          <motion.section className="results-section" {...sectionMotion}>
            <h2>Top candidates</h2>
            <p className="results-section__hint">Ranked by score. Each card compares the material with the NMC811 baseline.</p>
            {candidates.length === 0 ? (
              <p className="results-section__hint">No candidates were found for this task.</p>
            ) : (
              <motion.div
                className="material-card-grid"
                initial="hidden"
                whileInView="visible"
                viewport={{ once: true, margin: '-80px' }}
                transition={{ staggerChildren: 0.1 }}
              >
                {candidates.map((mat, idx) => (
                  <MaterialCard key={mat.id ?? mat.composition} material={mat} rank={idx + 1} />
                ))}
              </motion.div>
            )}
          </motion.section>

          {candidates.length > 0 && graphMaterial && (
            <motion.section className="results-section" {...sectionMotion}>
              <h2>Chemistry knowledge graph</h2>
              <p className="results-section__hint">Elements, properties and degradation modes linked to the selected material.</p>
              <div className="results-graph-select">
                <select
                  aria-label="Material for the knowledge graph"
                  value={graphMaterial}
                  onChange={(e) => setSelectedMaterial(e.target.value)}
                >
                  {candidates.map((mat, idx) => (
                    <option key={mat.composition} value={mat.composition}>
                      #{idx + 1} {mat.composition}
                    </option>
                  ))}
                </select>
              </div>
              <MaterialGraph materialName={graphMaterial} />
            </motion.section>
          )}
        </div>
      </main>
    </div>
  );
};

export default Results;
