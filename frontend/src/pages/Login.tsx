import { useState } from 'react';
import { ArrowLeft, ArrowRight, Check, GitBranch, Loader2, Sparkles } from 'lucide-react';
import { Link } from 'react-router-dom';
import AuraMark from '../components/shared/AuraMark';
import { hasSupabaseConfig, supabase } from '../lib/supabase';

const Login = () => {
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  const handleGitHubLogin = async () => {
    if (!supabase) {
      setErrorMessage('Authentication is not configured yet. Add your Supabase public URL and anonymous key to continue.');
      return;
    }

    try {
      setErrorMessage('');
      setLoading(true);
      const { error } = await supabase.auth.signInWithOAuth({
        provider: 'github',
        options: { redirectTo: `${window.location.origin}/dashboard` },
      });

      if (error) throw error;
    } catch (error: unknown) {
      setErrorMessage(error instanceof Error ? error.message : 'We could not start the sign-in flow. Please try again.');
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-page__aurora auth-page__aurora--one" />
      <div className="auth-page__aurora auth-page__aurora--two" />
      <div className="auth-page__grain" />

      <header className="auth-topbar">
        <Link to="/" className="auth-back"><ArrowLeft size={16} /> Back to AURA</Link>
        <AuraMark compact />
      </header>

      <main className="auth-layout">
        <section className="auth-intro">
          <span className="eyebrow"><Sparkles size={14} /> Your discovery space</span>
          <h1>Less searching.<br /><em>More seeing.</em></h1>
          <p>Bring your next battery-material question into a space designed to keep intuition, evidence, and possibility in one frame.</p>

          <div className="auth-intro__note">
            <div className="auth-intro__formula">LiNi<sub>0.8</sub>Mn<sub>0.1</sub>Co<sub>0.1</sub>O<sub>2</sub></div>
            <div>
              <span>Research field ready</span>
              <p>Evidence-linked candidate exploration for every session.</p>
            </div>
          </div>
        </section>

        <section className="auth-card" aria-labelledby="auth-heading">
          <div className="auth-card__heading">
            <span className="auth-card__label">Researcher access</span>
            <h2 id="auth-heading">Welcome to the<br />AURA field.</h2>
            <p>Sign in to start a private materials-discovery session.</p>
          </div>

          <button
            type="button"
            onClick={handleGitHubLogin}
            disabled={loading || !hasSupabaseConfig}
            className="auth-provider-button"
          >
            {loading ? <Loader2 className="animate-spin" size={19} /> : <GitBranch size={19} />}
            <span>{loading ? 'Opening secure sign in…' : 'Continue with GitHub'}</span>
            {!loading && <ArrowRight size={17} />}
          </button>

          {errorMessage && <p className="auth-error" role="alert">{errorMessage}</p>}

          <div className="auth-card__divider"><span>Protected research space</span></div>
          <ul className="auth-card__list">
            <li><Check size={15} /> Save and revisit your candidate trails</li>
            <li><Check size={15} /> Keep your material briefs organized</li>
            <li><Check size={15} /> Review evidence behind every recommendation</li>
          </ul>
          {!hasSupabaseConfig && <p className="auth-card__setup">Local preview mode: connect Supabase to enable sign-in.</p>}
        </section>
      </main>
    </div>
  );
};

export default Login;
