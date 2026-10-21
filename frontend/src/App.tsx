import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import LandingPage from './pages/LandingPage';
import Login from './pages/Login';
import Signup from './pages/Signup';
import Dashboard from './pages/Dashboard';
import Settings from './pages/Settings';
import { AuthProvider } from './contexts/AuthContext';
import { ProtectedRoute } from './components/shared/ProtectedRoute';

// The charts and force graph are only needed on the results page, so keep them out of the main bundle.
const Results = lazy(() => import('./pages/Results'));

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />
        <Route element={<ProtectedRoute />}>
          <Route path="/dashboard" element={<Navigate to="/dashboard/discovery" replace />} />
          <Route path="/dashboard/:view" element={<Dashboard />} />
          <Route path="/results/:taskId" element={<Suspense fallback={null}><Results /></Suspense>} />
          <Route path="/settings" element={<Settings />} />
        </Route>
        {/* Fallback route */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
