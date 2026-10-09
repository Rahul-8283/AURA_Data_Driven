import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import api from '../lib/api';
import type { ResearchStatusResponse } from '../types/research';

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

  return (
    <div className="workspace-shell" style={{ gridTemplateColumns: '1fr' }}>
      <main className="workspace-main">
        <header className="workspace-header">
          <button type="button" className="workspace-header__icon" onClick={() => navigate('/dashboard')} aria-label="Back to dashboard">
            <ArrowLeft size={18} />
          </button>
          <div className="workspace-breadcrumb"><strong>Research Report</strong></div>
        </header>

        <div className="workspace-content">
          {status.executive_summary && (
            <section style={{ marginBottom: 32 }}>
              <h2 style={{ fontFamily: 'var(--heading)', color: 'var(--paper)' }}>Executive Summary</h2>
              <p style={{ color: 'var(--text-muted)', whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>{status.executive_summary}</p>
            </section>
          )}

          <section>
            <h2 style={{ fontFamily: 'var(--heading)', color: 'var(--paper)' }}>Top Candidates</h2>
            <div style={{ display: 'grid', gap: 16, marginTop: 16 }}>
              {candidates.map((mat) => (
                <div
                  key={mat.id ?? mat.composition}
                  style={{
                    padding: 20,
                    border: '1px solid var(--line)',
                    borderRadius: 12,
                    background: 'var(--surface)',
                  }}
                >
                  <strong style={{ fontFamily: 'var(--mono)', color: 'var(--brass-bright)' }}>{mat.composition}</strong>
                  <div style={{ display: 'flex', gap: 24, margin: '10px 0', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    <span>Capacity: {mat.specific_capacity} mAh/g</span>
                    <span>Voltage: {mat.voltage} V</span>
                    <span>Cycle life: {mat.cycle_life}</span>
                    <span>Cost: ${mat.cost_estimate_usd_kg}/kg</span>
                    <span>Fitness: {mat.fitness.toFixed(2)}</span>
                  </div>
                  <p style={{ color: 'var(--text-dim)', fontSize: '0.8rem' }}>{mat.reasoning}</p>
                </div>
              ))}
              {candidates.length === 0 && <p style={{ color: 'var(--text-dim)' }}>No candidates were found for this task.</p>}
            </div>
          </section>
        </div>
      </main>
    </div>
  );
};

export default Results;
