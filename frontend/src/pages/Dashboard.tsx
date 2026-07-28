import { useEffect, useState } from 'react';
import type { User } from '@supabase/supabase-js';
import {
  Activity,
  ArrowRight,
  Bell,
  Bookmark,
  BrainCircuit,
  ChevronDown,
  CircleDot,
  Database,
  FileText,
  FlaskConical,
  Layers3,
  LogOut,
  MoreHorizontal,
  Plus,
  Search,
  Settings,
  Sparkles,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import AuraMark from '../components/shared/AuraMark';
import { supabase } from '../lib/supabase';

type WorkspaceUser = {
  name: string;
  email: string;
};

type Candidate = {
  id: string;
  composition: string;
  name: string;
  score: string;
  capacity: string;
  retention: string;
  confidence: string;
  tone: 'violet' | 'mint' | 'amber';
};

const candidates: Candidate[] = [
  { id: 'nmc-mg', composition: 'LiNi₀.₈₂Mn₀.₁₀Co₀.₀₆Mg₀.₀₂O₂', name: 'Mg-stabilized NMC', score: '0.91', capacity: '224 mAh/g', retention: '91%', confidence: 'High', tone: 'violet' },
  { id: 'nmc-al', composition: 'LiNi₀.₈₀Mn₀.₁₀Co₀.₀₇Al₀.₀₃O₂', name: 'Al-gradient NMC', score: '0.88', capacity: '219 mAh/g', retention: '93%', confidence: 'High', tone: 'mint' },
  { id: 'nmc-ti', composition: 'LiNi₀.₇₈Mn₀.₁₂Co₀.₀₈Ti₀.₀₂O₂', name: 'Ti-buffered NMC', score: '0.84', capacity: '213 mAh/g', retention: '95%', confidence: 'Medium', tone: 'amber' },
];

const workspaceUserFrom = (user: User): WorkspaceUser => ({
  name: user.user_metadata.user_name || user.user_metadata.full_name || user.email?.split('@')[0] || 'Researcher',
  email: user.email || 'researcher@aura.ai',
});

const previewUser: WorkspaceUser = { name: 'Dr. Aria Sen', email: 'aria@aura.local' };

const Dashboard = () => {
  const navigate = useNavigate();
  const isLocalPreview = import.meta.env.DEV && !supabase;
  const [user, setUser] = useState<WorkspaceUser | null>(() => isLocalPreview ? previewUser : null);
  const [loading, setLoading] = useState(() => !isLocalPreview);
  const previewMode = isLocalPreview;
  const [component, setComponent] = useState('Cathode');
  const [brief, setBrief] = useState('Design a nickel-rich cathode with high energy density, lower cobalt use, and stable cycling above 4.3 V.');
  const [runState, setRunState] = useState<'idle' | 'running' | 'complete'>('idle');
  const [savedCandidates, setSavedCandidates] = useState<string[]>([]);

  useEffect(() => {
    const authClient = supabase;
    if (!authClient) {
      if (!isLocalPreview) navigate('/login', { replace: true });
      return;
    }

    let isMounted = true;
    const checkUser = async () => {
      const { data: { session } } = await authClient.auth.getSession();
      if (!isMounted) return;

      if (!session) {
        navigate('/login', { replace: true });
      } else {
        setUser(workspaceUserFrom(session.user));
        setLoading(false);
      }
    };

    void checkUser();

    const { data: { subscription } } = authClient.auth.onAuthStateChange((_event, session) => {
      if (!session) {
        navigate('/login', { replace: true });
      } else {
        setUser(workspaceUserFrom(session.user));
        setLoading(false);
      }
    });

    return () => {
      isMounted = false;
      subscription.unsubscribe();
    };
  }, [isLocalPreview, navigate]);

  useEffect(() => {
    if (runState !== 'running') return undefined;
    const timer = window.setTimeout(() => setRunState('complete'), 2400);
    return () => window.clearTimeout(timer);
  }, [runState]);

  const handleSignOut = async () => {
    if (previewMode || !supabase) {
      navigate('/');
      return;
    }
    await supabase.auth.signOut();
  };

  const toggleSaved = (candidateId: string) => {
    setSavedCandidates((current) => current.includes(candidateId)
      ? current.filter((id) => id !== candidateId)
      : [...current, candidateId]);
  };

  if (loading) {
    return <div className="workspace-loading"><span className="workspace-loading__orb" /> Entering the AURA field…</div>;
  }

  const runLabel = runState === 'running' ? 'Exploring possibility space…' : runState === 'complete' ? 'Discovery refreshed' : 'Launch discovery';

  return (
    <div className="workspace-shell">
      <aside className="workspace-sidebar">
        <div className="workspace-sidebar__top">
          <AuraMark compact />
          <button type="button" className="sidebar-icon-button" aria-label="Create new research task"><Plus size={18} /></button>
        </div>

        <nav className="workspace-nav" aria-label="Research workspace navigation">
          <a className="workspace-nav__item workspace-nav__item--active" href="#research-brief"><Sparkles size={17} /> Discovery space</a>
          <a className="workspace-nav__item" href="#candidates"><FlaskConical size={17} /> Candidate field</a>
          <a className="workspace-nav__item" href="#evidence"><Database size={17} /> Evidence graph</a>
          <a className="workspace-nav__item" href="#reports"><FileText size={17} /> Research reports</a>
        </nav>

        <div className="workspace-sidebar__bottom">
          <div className="workspace-side-status"><span /><div><strong>Knowledge field</strong><small>43 sources connected</small></div></div>
          <button type="button" className="workspace-nav__item"><Settings size={17} /> Workspace settings</button>
          <button type="button" onClick={handleSignOut} className="workspace-nav__item workspace-nav__item--logout"><LogOut size={17} /> {previewMode ? 'Leave preview' : 'Sign out'}</button>
        </div>
      </aside>

      <main className="workspace-main">
        <header className="workspace-header">
          <div className="workspace-breadcrumb"><span>Research space</span><ChevronDown size={14} /><strong>High-energy cathodes</strong></div>
          <div className="workspace-header__actions">
            {previewMode && <span className="preview-pill">Local preview</span>}
            <button type="button" className="workspace-header__icon" aria-label="Search"><Search size={18} /></button>
            <button type="button" className="workspace-header__icon workspace-header__icon--notification" aria-label="Notifications"><Bell size={18} /><i /></button>
            <div className="workspace-user"><span>{user?.name.slice(0, 1).toUpperCase()}</span><div><strong>{user?.name}</strong><small>{user?.email}</small></div></div>
          </div>
        </header>

        <div className="workspace-content">
          <section id="research-brief" className="workspace-hero">
            <div className="workspace-hero__copy">
              <span className="workspace-eyebrow"><CircleDot size={14} /> Active material brief</span>
              <h1>Shape a better <em>charge.</em></h1>
              <p>Tell AURA where performance matters. It will map the viable material space around your intent.</p>
            </div>
            <div className="workspace-hero__score"><span>Research confidence</span><strong>87<small>%</small></strong><i /></div>
          </section>

          <section className="brief-composer">
            <div className="brief-composer__head"><div><span>Discovery brief</span><small>Natural language · chemistry-aware</small></div><button type="button" aria-label="More options"><MoreHorizontal size={20} /></button></div>
            <textarea value={brief} onChange={(event) => setBrief(event.target.value)} aria-label="Research brief" />
            <div className="brief-composer__footer">
              <div className="component-selector" role="group" aria-label="Battery component">
                {['Cathode', 'Anode', 'Electrolyte'].map((item) => <button key={item} type="button" onClick={() => setComponent(item)} className={component === item ? 'is-active' : ''}>{item}</button>)}
              </div>
              <button type="button" onClick={() => setRunState('running')} disabled={runState === 'running'} className="launch-button"><BrainCircuit size={17} /> {runLabel} <ArrowRight size={17} /></button>
            </div>
          </section>

          <section className="workspace-grid">
            <div id="candidates" className="candidate-section">
              <div className="workspace-section-heading"><div><span>Candidate field</span><h2>Promising directions</h2></div><button type="button">View all <ArrowRight size={15} /></button></div>
              <div className="candidate-list">
                {candidates.map((candidate, index) => (
                  <article className={`candidate-card candidate-card--${candidate.tone}`} key={candidate.id}>
                    <div className="candidate-card__rank">0{index + 1}</div>
                    <div className="candidate-card__body"><span>{candidate.name}</span><h3>{candidate.composition}</h3><div><small>Capacity <strong>{candidate.capacity}</strong></small><small>Retention <strong>{candidate.retention}</strong></small><small>Confidence <strong>{candidate.confidence}</strong></small></div></div>
                    <div className="candidate-card__score"><span>FIT</span><strong>{candidate.score}</strong></div>
                    <button type="button" onClick={() => toggleSaved(candidate.id)} className={savedCandidates.includes(candidate.id) ? 'candidate-card__save is-saved' : 'candidate-card__save'} aria-label={`Save ${candidate.name}`}><Bookmark size={17} /></button>
                  </article>
                ))}
              </div>
            </div>

            <aside id="evidence" className="evidence-panel">
              <div className="evidence-panel__head"><div><span>Evidence graph</span><h2>Why this path</h2></div><Layers3 size={19} /></div>
              <div className="mini-graph" aria-label="Material evidence graph visualization"><span className="mini-graph__line mini-graph__line--one" /><span className="mini-graph__line mini-graph__line--two" /><span className="mini-graph__line mini-graph__line--three" /><span className="mini-graph__node mini-graph__node--center">NMC</span><span className="mini-graph__node mini-graph__node--one">Mg</span><span className="mini-graph__node mini-graph__node--two">O₂</span><span className="mini-graph__node mini-graph__node--three">4.3V</span></div>
              <div className="evidence-panel__insight"><Activity size={17} /><p><strong>Stability signal rising.</strong> Mg substitution appears repeatedly alongside reduced cation mixing.</p></div>
              <button type="button" className="evidence-panel__button">Open evidence trail <ArrowRight size={15} /></button>
            </aside>
          </section>

          <section id="reports" className="workspace-activity"><div><span className="workspace-eyebrow"><Activity size={14} /> Discovery activity</span><p>{runState === 'running' ? 'GraphRAG is comparing dopant effects across the connected literature.' : runState === 'complete' ? 'Candidate rankings updated with fresh evidence checks.' : 'Your research field is ready for the next question.'}</p></div><div className="workspace-activity__progress"><i className={runState === 'running' ? 'is-running' : runState === 'complete' ? 'is-complete' : ''} /><span>{runState === 'running' ? 'Building' : runState === 'complete' ? 'Complete' : 'Standing by'}</span></div></section>
        </div>
      </main>
    </div>
  );
};

export default Dashboard;
