import { create } from 'zustand';

type TaskStatus = 'idle' | 'processing' | 'completed' | 'error';

interface ResearchState {
  currentTaskId: string | null;
  taskStatus: TaskStatus;
  progress: number;
  logs: string[];
  setTaskId: (id: string) => void;
  updateStatus: (status: TaskStatus, progress: number) => void;
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
}));
