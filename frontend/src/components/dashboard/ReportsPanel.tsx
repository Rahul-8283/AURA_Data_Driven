import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FileText, Loader2 } from 'lucide-react';
import { supabase } from '../../lib/supabase';
import { useAuth } from '../../contexts/useAuth';

interface ReportRow {
  id: string;
  prompt: string;
  status: string;
  created_at: string;
}

export default function ReportsPanel() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [reports, setReports] = useState<ReportRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const loadReports = async () => {
      if (!user || !supabase) {
        setLoading(false);
        return;
      }
      const client = supabase;
      setLoading(true);
      setError('');
      try {
        const { data, error: fetchError } = await client
          .from('ResearchTasks')
          .select('id, prompt, status, created_at')
          .eq('user_id', user.id)
          .order('created_at', { ascending: false });

        if (fetchError) throw fetchError;
        setReports(data ?? []);
      } catch {
        setError('Could not load your research reports.');
      } finally {
        setLoading(false);
      }
    };

    void loadReports();
  }, [user]);

  if (!user) {
    return <p className="reports-panel__empty">Sign in to see your research reports.</p>;
  }

  if (loading) {
    return (
      <div className="reports-panel__status">
        <Loader2 size={16} className="animate-spin" /> Loading reports…
      </div>
    );
  }

  if (error) {
    return <p className="reports-panel__status">{error}</p>;
  }

  if (reports.length === 0) {
    return <p className="reports-panel__empty">No research reports yet. Start a discovery in the chat to see results here.</p>;
  }

  return (
    <div className="reports-panel">
      {reports.map((report) => {
        const isCompleted = report.status === 'completed';
        return (
          <button
            key={report.id}
            type="button"
            className="reports-panel__item"
            disabled={!isCompleted}
            onClick={() => navigate(`/results/${report.id}`)}
            title={isCompleted ? 'View results' : `Status: ${report.status}`}
          >
            <FileText size={16} />
            <div className="reports-panel__item-body">
              <strong>{report.prompt}</strong>
              <small>{new Date(report.created_at).toLocaleString()}</small>
            </div>
            <span className={`reports-panel__status-pill reports-panel__status-pill--${report.status}`}>
              {report.status}
            </span>
          </button>
        );
      })}
    </div>
  );
}
