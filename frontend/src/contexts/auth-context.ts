import { createContext } from 'react';
import type { User, Session } from '@supabase/supabase-js';

export interface AuthContextType {
  user: User | null;
  session: Session | null;
  isLoading: boolean;
}

export const AuthContext = createContext<AuthContextType>({ user: null, session: null, isLoading: true });
