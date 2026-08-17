import { useEffect, useState } from 'react';
import type { User } from '@supabase/supabase-js';
import {
  Bell,
  ChevronDown,
  Database,
  FileText,
  FlaskConical,
  LogOut,
  Plus,
  Search,
  Settings,
  Sparkles,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import AuraMark from '../components/shared/AuraMark';
import { supabase } from '../lib/supabase';
import ChatInterface from '../components/dashboard/ChatInterface';

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
          <a className="workspace-nav__item workspace-nav__item--active" href="#discovery"><Sparkles size={17} /> Discovery space</a>
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
          <ChatInterface />
        </div>
      </main>
    </div>
  );
};

export default Dashboard;
