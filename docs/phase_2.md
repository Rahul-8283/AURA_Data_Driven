# Phase 2: Authentication & User Dashboard (Detailed Implementation Plan)

## 1. Objective and Scope
The goal of Phase 2 is to build the frontend architecture, establish secure user authentication via Supabase, and create the foundational dashboard where researchers will submit their battery material requirements. By the end of this phase, a user should be able to sign up, log in, view a protected dashboard, and submit a form that successfully communicates securely with the FastAPI backend.

---

## 2. Supabase Authentication Setup (Frontend)

### 2.1 Initialization (`src/lib/supabase.ts`)
We will use the official `@supabase/supabase-js` client.
```typescript
import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error("Missing Supabase environment variables")
}

export const supabase = createClient(supabaseUrl, supabaseAnonKey)
```

### 2.2 Auth Context Provider (`src/contexts/AuthContext.tsx`)
Create a React Context to manage the user session globally.
- Implement `useEffect` to listen to `supabase.auth.onAuthStateChange`.
- Export custom hook `useAuth()` exposing `user`, `session`, and `isLoading`.

### 2.3 Login & Registration UI (`src/pages/Auth/`)
- **Login Component:** Use TailwindCSS for a modern, glassmorphic design. Include email/password fields and OAuth buttons (Google/GitHub if desired).
- **Signup Component:** Standard email registration flow.
- Add `framer-motion` for smooth page transitions between Login and Signup.

---

## 3. Global State Management (Zustand)

### 3.1 Store Definition (`src/store/useResearchStore.ts`)
Create a Zustand store to handle the state of the active research task.
```typescript
import { create } from 'zustand'

interface ResearchState {
  currentTaskId: string | null;
  taskStatus: 'idle' | 'processing' | 'completed' | 'error';
  progress: number;
  logs: string[];
  setTaskId: (id: string) => void;
  updateStatus: (status: any, progress: number) => void;
  addLog: (log: string) => void;
  reset: () => void;
}

export const useResearchStore = create<ResearchState>((set) => ({
  currentTaskId: null,
  taskStatus: 'idle',
  progress: 0,
  logs: [],
  setTaskId: (id) => set({ currentTaskId: id, taskStatus: 'processing' }),
  updateStatus: (status, progress) => set({ taskStatus: status, progress }),
  addLog: (log) => set((state) => ({ logs: [...state.logs, log] })),
  reset: () => set({ currentTaskId: null, taskStatus: 'idle', progress: 0, logs: [] }),
}))
```

---

## 4. Protected Routing (`src/App.tsx`)

Implement `react-router-dom` with route guards.
- Wrap the `<Dashboard />` route in a `<ProtectedRoute>` component that checks `useAuth().session`. If null, redirect to `/login`.
- Define routes:
  - `/` -> Landing Page
  - `/login` -> Auth Page
  - `/dashboard` -> Main Application Interface
  - `/results/:taskId` -> Research Output View

---

## 5. Main Dashboard UI (`src/pages/Dashboard/`)

### 5.1 Sidebar Layout (`src/components/Layout/Sidebar.tsx`)
- Use `lucide-react` for icons (e.g., Home, History, Settings).
- Provide navigation to past research runs (fetching from Supabase database).

### 5.2 Research Input Form (`src/components/Dashboard/RequirementForm.tsx`)
This is the core interaction point.
- **Form Fields:**
  - `Base Component Type`: Dropdown (Cathode, Anode, Solid Electrolyte).
  - `Target Capacity`: Number input (mAh/g).
  - `Target Cycle Life`: Number input.
  - `Custom Instructions`: Textarea (e.g., "Must avoid Cobalt due to cost constraints").
- **Validation:** Use `react-hook-form` and `zod` to validate inputs before submission.

---

## 6. Frontend-Backend Secure Integration

### 6.1 Axios Interceptor Setup (`src/lib/api.ts`)
To securely communicate with FastAPI, we must attach the Supabase JWT token to every request.
```typescript
import axios from 'axios';
import { supabase } from './supabase';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1',
});

api.interceptors.request.use(async (config) => {
  const { data: { session } } = await supabase.auth.getSession();
  if (session?.access_token) {
    config.headers.Authorization = `Bearer ${session.access_token}`;
  }
  return config;
});

export default api;
```

### 6.2 FastAPI JWT Validation (Backend)
- In the FastAPI backend (`app/core/security.py`), implement a dependency to decode and verify the JWT sent from the React frontend.
- Ensure the JWT is signed with the `SUPABASE_JWT_SECRET`.
- Apply this dependency to the `POST /api/v1/research/start` endpoint.

---

## 7. Execution and Verification Checklist
1. User can successfully sign up and log in via the React frontend.
2. The user is redirected to `/dashboard` upon successful login.
3. The JWT token is visible in local storage or memory.
4. Submitting the Research Input Form successfully triggers the `axios` POST request to the backend.
5. The backend validates the JWT and rejects unauthorized requests with a 401 error.
6. The Zustand store successfully updates to `processing` state upon receiving a dummy `task_id` from the backend.
