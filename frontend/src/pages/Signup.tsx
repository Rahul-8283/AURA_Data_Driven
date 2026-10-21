import { useState } from 'react';
import { ArrowLeft, ArrowRight, Loader2 } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import AuraMark from '../components/shared/AuraMark';
import { supabase } from '../lib/supabase';

const Signup = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!supabase) {
      setErrorMessage('Authentication is not configured yet.');
      return;
    }

    if (password !== confirmPassword) {
      setErrorMessage('Passwords do not match.');
      return;
    }

    if (password.length < 6) {
      setErrorMessage('Password must be at least 6 characters.');
      return;
    }

    try {
      setErrorMessage('');
      setLoading(true);
      
      const { error } = await supabase.auth.signUp({
        email,
        password,
      });

      if (error) throw error;
      
      // Successfully signed up, redirect to dashboard or login
      navigate('/dashboard/discovery');
    } catch (error: unknown) {
      setErrorMessage(error instanceof Error ? error.message : 'Signup failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <header className="auth-topbar">
        <Link to="/" className="auth-back"><ArrowLeft size={16} /> Back to AURA</Link>
        <AuraMark compact />
      </header>

      <main className="auth-layout">
        <section className="auth-intro">
          <span className="eyebrow">Join the network</span>
          <h1>Start discovering.<br /><em>Start building.</em></h1>
          <p>Create an account to track your material searches and connect with the GraphRAG backend.</p>

          <div className="auth-intro__note">
            <div className="auth-intro__formula">LiFePO<sub>4</sub></div>
            <div>
              <span>Secure & Private</span>
              <p>Your research trails are strictly isolated to your workspace.</p>
            </div>
          </div>
        </section>

        <section className="auth-card" aria-labelledby="auth-heading">
          <div className="auth-card__heading">
            <span className="auth-card__label">New Researcher</span>
            <h2 id="auth-heading">Create your<br />AURA account.</h2>
          </div>

          <form onSubmit={handleSignup} className="auth-form">
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
            <input 
              type="password" 
              placeholder="Confirm Password" 
              className="auth-input"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
            />

            <button
              type="submit"
              disabled={loading}
              className="auth-submit-button"
            >
              {loading ? <Loader2 size={19} /> : 'Create Account'}
              {!loading && <ArrowRight size={17} />}
            </button>
          </form>

          {errorMessage && <p className="auth-error" role="alert">{errorMessage}</p>}

          <Link to="/login" className="auth-footer-link">
            Already have an account? Log in here
          </Link>
        </section>
      </main>
    </div>
  );
};

export default Signup;
