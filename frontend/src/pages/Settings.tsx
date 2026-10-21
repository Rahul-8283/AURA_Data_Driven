import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Bell,
  ChevronDown,
  Database,
  FileText,
  LogOut,
  MessageSquare,
  Plus,
  Search,
  Settings as SettingsIcon,
  User,
  Shield,
  Loader2,
  CheckCircle2,
  AlertCircle
} from 'lucide-react';
import AuraMark from '../components/shared/AuraMark';
import { useAuth } from '../contexts/useAuth';
import { supabase } from '../lib/supabase';

const Settings: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();

  const [name, setName] = useState(user?.user_metadata?.user_name || user?.user_metadata?.full_name || user?.email?.split('@')[0] || '');
  const [isUpdatingName, setIsUpdatingName] = useState(false);
  const [nameStatus, setNameStatus] = useState<'idle' | 'success' | 'error'>('idle');

  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isUpdatingPassword, setIsUpdatingPassword] = useState(false);
  const [passwordStatus, setPasswordStatus] = useState<'idle' | 'success' | 'error'>('idle');
  const [passwordErrorMsg, setPasswordErrorMsg] = useState('');

  const previewMode = import.meta.env.VITE_MODE === 'development';

  const handleSignOut = async () => {
    if (previewMode || !supabase) {
      navigate('/');
      return;
    }
    try {
      await supabase.auth.signOut();
      navigate('/login');
    } catch (error) {
      console.error('Error signing out:', error);
    }
  };

  const handleUpdateName = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!supabase) return;
    setIsUpdatingName(true);
    setNameStatus('idle');
    try {
      const { error } = await supabase.auth.updateUser({
        data: { full_name: name }
      });
      if (error) throw error;
      setNameStatus('success');
      setTimeout(() => setNameStatus('idle'), 3000);
    } catch (error) {
      console.error('Error updating name:', error);
      setNameStatus('error');
    } finally {
      setIsUpdatingName(false);
    }
  };

  const handleUpdatePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password !== confirmPassword) {
      setPasswordStatus('error');
      setPasswordErrorMsg('Passwords do not match');
      return;
    }
    if (password.length < 6) {
      setPasswordStatus('error');
      setPasswordErrorMsg('Password must be at least 6 characters');
      return;
    }

    if (!supabase) return;
    setIsUpdatingPassword(true);
    setPasswordStatus('idle');
    try {
      const { error } = await supabase.auth.updateUser({ password });
      if (error) throw error;
      setPasswordStatus('success');
      setPassword('');
      setConfirmPassword('');
      setTimeout(() => setPasswordStatus('idle'), 3000);
    } catch (error: unknown) {
      console.error('Error updating password:', error);
      setPasswordStatus('error');
      setPasswordErrorMsg(error instanceof Error ? error.message : 'Failed to update password');
    } finally {
      setIsUpdatingPassword(false);
    }
  };

  return (
    <div className="workspace-shell">
      {/* Sidebar (Reused from Dashboard) */}
      <aside className="workspace-sidebar">
        <div className="workspace-sidebar__top">
          <AuraMark compact />
          <button type="button" className="sidebar-icon-button" aria-label="Create new research task"><Plus size={18} /></button>
        </div>

        <nav className="workspace-nav" aria-label="Research workspace navigation">
          <button type="button" onClick={() => navigate('/dashboard/discovery')} className="workspace-nav__item"><MessageSquare size={17} /> Discovery space</button>
          <button type="button" className="workspace-nav__item"><Database size={17} /> Evidence graph</button>
          <button type="button" className="workspace-nav__item"><FileText size={17} /> Research reports</button>
        </nav>

        <div className="workspace-sidebar__bottom">
          <button type="button" className="workspace-nav__item workspace-nav__item--active"><SettingsIcon size={17} /> Settings</button>
          <button type="button" onClick={handleSignOut} className="workspace-nav__item workspace-nav__item--logout"><LogOut size={17} /> {previewMode ? 'Leave preview' : 'Sign out'}</button>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="workspace-main">
        <header className="workspace-header">
          <div className="workspace-breadcrumb"><span>AURA System</span><ChevronDown size={14} /><strong>Workspace Settings</strong></div>
          <div className="workspace-header__actions">
            <button type="button" className="workspace-header__icon" aria-label="Search"><Search size={18} /></button>
            <button type="button" className="workspace-header__icon workspace-header__icon--notification" aria-label="Notifications"><Bell size={18} /><i /></button>
            <div className="workspace-user">
              <span>{(user?.user_metadata?.user_name || user?.user_metadata?.full_name || user?.email || '?').slice(0, 1).toUpperCase()}</span>
              <div>
                <strong>{user?.user_metadata?.user_name || user?.user_metadata?.full_name || user?.email?.split('@')[0] || 'User'}</strong>
                <small>{user?.email}</small>
              </div>
            </div>
          </div>
        </header>

        <div className="workspace-content" style={{ padding: '2rem', maxWidth: '800px', margin: '0 auto', width: '100%' }}>
          <div className="flex flex-col gap-8">
            <div>
              <h1 className="text-2xl font-bold mb-2 tracking-tight">Settings</h1>
              <p className="text-sm opacity-60">Manage your profile and security preferences.</p>
            </div>

            {/* Profile Settings */}
            <section className="bg-black/20 border border-white/5 rounded-xl p-6 relative overflow-hidden">
              <div className="absolute top-0 right-0 p-6 opacity-10">
                <User size={64} />
              </div>
              <h2 className="text-lg font-semibold mb-6 flex items-center gap-2"><User size={18} /> Profile Details</h2>
              <form onSubmit={handleUpdateName} className="flex flex-col gap-4 max-w-md relative z-10">
                <div className="flex flex-col gap-2">
                  <label className="text-xs uppercase tracking-wider opacity-70">Email Address</label>
                  <input
                    type="email"
                    value={user?.email || ''}
                    disabled
                    className="bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-sm opacity-50 cursor-not-allowed outline-none"
                  />
                  <span className="text-xs opacity-50">Email cannot be changed directly.</span>
                </div>

                <div className="flex flex-col gap-2">
                  <label className="text-xs uppercase tracking-wider opacity-70">Display Name</label>
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="E.g. Dr. Jane Smith"
                    className="bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-sm focus:border-white/30 outline-none transition-colors"
                  />
                </div>

                <div className="pt-2 flex items-center gap-4">
                  <button
                    type="submit"
                    disabled={isUpdatingName || !name || name === (user?.user_metadata?.user_name || user?.user_metadata?.full_name || user?.email?.split('@')[0])}
                    className="bg-white text-black px-6 py-2 rounded-lg text-sm font-semibold hover:bg-white/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
                  >
                    {isUpdatingName && <Loader2 size={14} className="animate-spin" />}
                    Save Changes
                  </button>
                  {nameStatus === 'success' && <span className="text-green-400 text-sm flex items-center gap-1"><CheckCircle2 size={14} /> Updated</span>}
                  {nameStatus === 'error' && <span className="text-red-400 text-sm flex items-center gap-1"><AlertCircle size={14} /> Failed</span>}
                </div>
              </form>
            </section>

            {/* Security Settings */}
            <section className="bg-black/20 border border-white/5 rounded-xl p-6 relative overflow-hidden">
              <div className="absolute top-0 right-0 p-6 opacity-10">
                <Shield size={64} />
              </div>
              <h2 className="text-lg font-semibold mb-6 flex items-center gap-2 text-red-400/90"><Shield size={18} /> Security</h2>
              <form onSubmit={handleUpdatePassword} className="flex flex-col gap-4 max-w-md relative z-10">

                <div className="flex flex-col gap-2">
                  <label className="text-xs uppercase tracking-wider opacity-70">New Password</label>
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    className="bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-sm focus:border-white/30 outline-none transition-colors"
                  />
                </div>

                <div className="flex flex-col gap-2">
                  <label className="text-xs uppercase tracking-wider opacity-70">Confirm New Password</label>
                  <input
                    type="password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="••••••••"
                    className="bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-sm focus:border-white/30 outline-none transition-colors"
                  />
                </div>

                <div className="pt-2 flex items-center gap-4">
                  <button
                    type="submit"
                    disabled={isUpdatingPassword || !password || !confirmPassword}
                    className="bg-red-500/20 text-red-400 border border-red-500/30 px-6 py-2 rounded-lg text-sm font-semibold hover:bg-red-500/30 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
                  >
                    {isUpdatingPassword && <Loader2 size={14} className="animate-spin" />}
                    Update Password
                  </button>
                  {passwordStatus === 'success' && <span className="text-green-400 text-sm flex items-center gap-1"><CheckCircle2 size={14} /> Password changed</span>}
                  {passwordStatus === 'error' && <span className="text-red-400 text-sm flex items-center gap-1"><AlertCircle size={14} /> {passwordErrorMsg}</span>}
                </div>
              </form>
            </section>

          </div>
        </div>
      </main>
    </div>
  );
};

export default Settings;
