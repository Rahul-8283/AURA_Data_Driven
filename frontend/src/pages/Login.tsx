import React, { useState } from 'react';
import { supabase } from '../lib/supabase';
import { GitBranch, Loader2, ArrowLeft } from 'lucide-react';
import { Link } from 'react-router-dom';

const Login: React.FC = () => {
  const [loading, setLoading] = useState(false);

  const handleGitHubLogin = async () => {
    try {
      setLoading(true);
      const { error } = await supabase.auth.signInWithOAuth({
        provider: 'github',
        options: {
          redirectTo: 'http://localhost:5173/dashboard'
        }
      });
      if (error) throw error;
    } catch (error: any) {
      console.error('Error logging in:', error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0a0a] flex flex-col justify-center items-center p-4 relative">
      <Link to="/" className="absolute top-8 left-8 text-gray-500 hover:text-white flex items-center gap-2 transition-colors text-sm font-bold">
        <ArrowLeft className="w-4 h-4" />
        BACK
      </Link>
      
      <div className="max-w-sm w-full bg-[#111] p-8 rounded-sm border border-[#222] text-center">
        
        <div className="text-4xl font-logo tracking-widest text-gray-200 mb-6">monomelt</div>
        <p className="text-gray-400 mb-10 text-sm leading-relaxed">Sign in to start transforming your legacy monoliths into modern microservices.</p>
        
        <button
          onClick={handleGitHubLogin}
          disabled={loading}
          className="w-full bg-white text-black font-bold py-3 px-4 rounded-sm flex items-center justify-center gap-3 hover:bg-gray-200 transition-colors disabled:opacity-70 text-sm"
        >
          {loading ? (
            <Loader2 className="w-5 h-5 animate-spin" />
          ) : (
            <>
              <GitBranch className="w-5 h-5" />
              Sign in with GitHub
            </>
          )}
        </button>
      </div>
    </div>
  );
};

export default Login;
