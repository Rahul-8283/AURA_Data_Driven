import { useEffect, useState } from 'react';
import type { User } from '@supabase/supabase-js';
import {
  Bell,
  ChevronDown,
  Database,
  FileText,
  LogOut,
  MessageSquare,
  Plus,
  Search,
  Settings,
} from 'lucide-react';
import { Navigate, useNavigate, useParams } from 'react-router-dom';
import AuraMark from '../components/shared/AuraMark';
import { supabase } from '../lib/supabase';
import ChatInterface from '../components/dashboard/ChatInterface';
import ReportsPanel from '../components/dashboard/ReportsPanel';
import EvidencePanel from '../components/dashboard/EvidencePanel';

type WorkspaceView = 'discovery' | 'evidence' | 'reports';

const WORKSPACE_VIEWS: readonly WorkspaceView[] = ['discovery', 'evidence', 'reports'];

const isWorkspaceView = (value: string | undefined): value is WorkspaceView =>
  WORKSPACE_VIEWS.includes(value as WorkspaceView);

const VIEW_LABELS: Record<WorkspaceView, string> = {
  discovery: 'Discovery space',
  evidence: 'Evidence graph',
  reports: 'Research reports',
};

type WorkspaceUser = {
  name: string;
  email: string;
};

const workspaceUserFrom = (user: User): WorkspaceUser => ({
  name: user.user_metadata.user_name || user.user_metadata.full_name || user.email?.split('@')[0] || 'Researcher',
  email: user.email || 'researcher@aura.ai',
});

const previewUser: WorkspaceUser = { name: 'Dr. Aria Sen', email: 'aria@aura.local' };

const Dashboard = () => {
  const navigate = useNavigate();
  const { view } = useParams<{ view: string }>();
  const isLocalPreview = import.meta.env.DEV && !supabase;
  const [user, setUser] = useState<WorkspaceUser | null>(() => isLocalPreview ? previewUser : null);
  const [loading, setLoading] = useState(() => !isLocalPreview);
  const previewMode = isLocalPreview;

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

  const handleSignOut = async () => {
    if (previewMode || !supabase) {
      navigate('/');
      return;
    }
    await supabase.auth.signOut();
  };

  if (!isWorkspaceView(view)) {
    return <Navigate to="/dashboard/discovery" replace />;
  }
  const activeView = view;

  if (loading) {
    return <div className="workspace-loading"><span className="workspace-loading__orb" /> Entering the AURA field…</div>;
  }

  return (
    <div className="workspace-shell">
      <aside className="workspace-sidebar">
        <div className="workspace-sidebar__top">
          <AuraMark compact />
          <button type="button" className="sidebar-icon-button" aria-label="Create new research task"><Plus size={18} /></button>
        </div>

        <nav className="workspace-nav" aria-label="Research workspace navigation">
          <button
            type="button"
            className={`workspace-nav__item ${activeView === 'discovery' ? 'workspace-nav__item--active' : ''}`}
            onClick={() => navigate('/dashboard/discovery')}
          >
            <MessageSquare size={17} /> Discovery space
          </button>
          <button
            type="button"
            className={`workspace-nav__item ${activeView === 'evidence' ? 'workspace-nav__item--active' : ''}`}
            onClick={() => navigate('/dashboard/evidence')}
          >
            <Database size={17} /> Evidence graph
          </button>
          <button
            type="button"
            className={`workspace-nav__item ${activeView === 'reports' ? 'workspace-nav__item--active' : ''}`}
            onClick={() => navigate('/dashboard/reports')}
          >
            <FileText size={17} /> Research reports
          </button>
        </nav>

        <div className="workspace-sidebar__bottom">
          <button type="button" onClick={() => navigate('/settings')} className="workspace-nav__item"><Settings size={17} /> Settings</button>
          <button type="button" onClick={handleSignOut} className="workspace-nav__item workspace-nav__item--logout"><LogOut size={17} /> {previewMode ? 'Leave preview' : 'Sign out'}</button>
        </div>
      </aside>

      <main className="workspace-main">
        <header className="workspace-header">
          <div className="workspace-breadcrumb"><span>Research space</span><ChevronDown size={14} /><strong>{VIEW_LABELS[activeView]}</strong></div>
          <div className="workspace-header__actions">
            <button type="button" className="workspace-header__icon" aria-label="Search"><Search size={18} /></button>
            <button type="button" className="workspace-header__icon workspace-header__icon--notification" aria-label="Notifications"><Bell size={18} /><i /></button>
            <div className="workspace-user"><span>{user?.name.slice(0, 1).toUpperCase()}</span><div><strong>{user?.name}</strong><small>{user?.email}</small></div></div>
          </div>
        </header>

        <div className="workspace-content">
          {activeView === 'discovery' && <ChatInterface />}
          {activeView === 'reports' && <ReportsPanel />}
          {activeView === 'evidence' && <EvidencePanel />}
        </div>
      </main>
    </div>
  );
};

export default Dashboard;
