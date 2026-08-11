import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

export const ProtectedRoute = () => {
  const { session, isLoading } = useAuth();
  const isLocalPreview = import.meta.env.DEV && !import.meta.env.VITE_SUPABASE_URL;

  if (isLoading && !isLocalPreview) {
    return <div className="workspace-loading"><span className="workspace-loading__orb" /> Loading...</div>;
  }

  if (!session && !isLocalPreview) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
};
