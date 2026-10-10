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

  return (
    <div className="workspace-shell" style={{ gridTemplateColumns: '1fr' }}>
      <main className="workspace-main">
        <header className="workspace-header">
          <button type="button" className="workspace-header__icon" onClick={() => navigate('/dashboard')} aria-label="Back to dashboard">
            <ArrowLeft size={18} />
          </button>
          <div className="workspace-breadcrumb"><strong>Research Report</strong></div>
          <div className="workspace-header__actions">
            <button type="button" className="results-download-btn" onClick={handleDownloadPdf} disabled={exporting}>
              {exporting ? <Loader2 size={16} className="animate-spin" /> : <Download size={16} />}
              {exporting ? 'Preparing PDF…' : 'Download Full Report'}
            </button>
          </div>
        </header>

        <div className="results-page" ref={reportRef}>
          {status.executive_summary && (
            <motion.section
              className="results-section"
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true, margin: '-80px' }}
              variants={fadeInUp}
            >
              <h2>Executive Summary</h2>
              <p className="results-summary">{status.executive_summary}</p>
            </motion.section>
          )}

          {history.length > 0 && (
            <motion.section
              className="results-section"
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true, margin: '-80px' }}
              variants={fadeInUp}
            >
              <h2>Evolution Progress</h2>
              <EvolutionChart data={history} />
            </motion.section>
          )}

          <motion.section
            className="results-section"
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: '-80px' }}
            variants={fadeInUp}
          >
            <h2>Top Candidates</h2>
            {candidates.length === 0 ? (
              <p style={{ color: 'var(--text-dim)' }}>No candidates were found for this task.</p>
            ) : (
              <motion.div
                className="material-card-grid"
                initial="hidden"
                whileInView="visible"
                viewport={{ once: true, margin: '-80px' }}
                transition={{ staggerChildren: 0.12 }}
              >
                {candidates.map((mat, idx) => (
                  <MaterialCard key={mat.id ?? mat.composition} material={mat} rank={idx + 1} />
                ))}
              </motion.div>
            )}
          </motion.section>

          {candidates.length > 0 && graphMaterial && (
            <motion.section
              className="results-section"
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true, margin: '-80px' }}
              variants={fadeInUp}
            >
              <div className="results-section__header-row">
                <h2>Chemistry Knowledge Graph</h2>
                <select
                  className="material-graph__select"
                  value={graphMaterial}
                  onChange={(e) => setSelectedMaterial(e.target.value)}
                >
                  {candidates.map((mat) => (
                    <option key={mat.composition} value={mat.composition}>{mat.composition}</option>
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
