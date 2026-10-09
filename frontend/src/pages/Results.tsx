import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import api from '../lib/api';
import type { ResearchStatusResponse } from '../types/research';
import MaterialCard from '../components/results/MaterialCard';
import EvolutionChart from '../components/results/EvolutionChart';

const Results = () => {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();
  const [status, setStatus] = useState<ResearchStatusResponse | null>(null);
  const [error, setError] = useState('');

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

  return (
    <div className="workspace-shell" style={{ gridTemplateColumns: '1fr' }}>
      <main className="workspace-main">
        <header className="workspace-header">
          <button type="button" className="workspace-header__icon" onClick={() => navigate('/dashboard')} aria-label="Back to dashboard">
            <ArrowLeft size={18} />
          </button>
          <div className="workspace-breadcrumb"><strong>Research Report</strong></div>
        </header>

        <div className="results-page">
          {status.executive_summary && (
            <section className="results-section">
              <h2>Executive Summary</h2>
              <p className="results-summary">{status.executive_summary}</p>
            </section>
          )}

          {history.length > 0 && (
            <section className="results-section">
              <h2>Evolution Progress</h2>
              <EvolutionChart data={history} />
            </section>
          )}

          <section className="results-section">
            <h2>Top Candidates</h2>
            {candidates.length === 0 ? (
              <p style={{ color: 'var(--text-dim)' }}>No candidates were found for this task.</p>
            ) : (
              <div className="material-card-grid">
                {candidates.map((mat, idx) => (
                  <MaterialCard key={mat.id ?? mat.composition} material={mat} rank={idx + 1} />
                ))}
              </div>
            )}
          </section>
        </div>
      </main>
    </div>
  );
};

export default Results;
