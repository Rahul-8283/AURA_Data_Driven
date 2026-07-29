import { useState } from 'react';
import { ArrowLeft, ArrowRight, GitBranch, Loader2, Sparkles } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import AuraMark from '../components/shared/AuraMark';
import { hasSupabaseConfig, supabase } from '../lib/supabase';

const Login = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleEmailLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!supabase) {
      setErrorMessage('Authentication is not configured yet.');
      return;
    }

    try {
      setErrorMessage('');
      setLoading(true);
      const { error } = await supabase.auth.signInWithPassword({
        email,
        password,
      });

      if (error) throw error;
      
      // Redirect to dashboard on success
      navigate('/dashboard');
    } catch (error: unknown) {
      setErrorMessage(error instanceof Error ? error.message : 'Invalid login credentials. Please try again.');
    } finally {
      setLoading(false);
    }
  };

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
        <motion.section 
          initial={{ opacity: 0, x: -30 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6 }}
          className="auth-intro"
        >
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
        </motion.section>

        <motion.section 
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="auth-card" aria-labelledby="auth-heading"
        >
          <div className="auth-card__heading">
            <span className="auth-card__label">Researcher access</span>
            <h2 id="auth-heading">Welcome to the<br />AURA field.</h2>
            <p>Sign in to start a private materials-discovery session.</p>
          </div>

          <form onSubmit={handleEmailLogin} className="auth-form">
            <input 
              type="email" 
              placeholder="Email address" 
              className="auth-input"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
            <input 
              type="password" 
              placeholder="Password" 
              className="auth-input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />

            <button
              type="submit"
              disabled={loading || !hasSupabaseConfig}
              className="auth-submit-button"
            >
              {loading ? <Loader2 size={19} /> : 'Log In'}
              {!loading && <ArrowRight size={17} />}
            </button>
          </form>

          <div className="auth-card__divider"><span>OR</span></div>

          <button
            type="button"
            onClick={handleGitHubLogin}
            disabled={loading || !hasSupabaseConfig}
            className="auth-provider-button"
          >
            {loading ? <Loader2 size={19} /> : <GitBranch size={19} />}
            <span>{loading ? 'Opening secure sign in…' : 'Continue with GitHub'}</span>
          </button>

          {errorMessage && <p className="auth-error" role="alert">{errorMessage}</p>}

          <Link to="/signup" className="auth-footer-link">
            Don't have an account? Sign up here
          </Link>

        </motion.section>
      </main>
    </div>
  );
};

export default Login;
