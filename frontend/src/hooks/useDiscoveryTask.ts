import { useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../lib/api';
import { useResearchStore } from '../store/useResearchStore';
import type { ResearchStatusResponse } from '../types/research';

const POLL_INTERVAL_MS = 3000;

/**
 * Starts a full GA discovery run and polls its status until completion,
 * then redirects to the results page. Encapsulated here so the chat UI
 * doesn't have to manage interval lifecycles directly.
 */
export function useDiscoveryTask() {
  const navigate = useNavigate();
  const { setTaskId, updateStatus, addLog, reset } = useResearchStore();
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const startDiscovery = useCallback(
    async (prompt: string): Promise<string> => {
      reset();
      const { data } = await api.post<{ task_id: string; status: string }>('/api/v1/research/start', { prompt });
      const taskId = data.task_id;
      setTaskId(taskId);
      addLog(`Discovery task ${taskId} started.`);

      stopPolling();
      pollRef.current = setInterval(async () => {
        try {
          const { data: status } = await api.get<ResearchStatusResponse>(`/api/v1/research/status/${taskId}`);

          if (status.status === 'Complete') {
            stopPolling();
            updateStatus('completed', status.generation ?? 0, status.best_score ?? 0);
            navigate(`/results/${taskId}`);
          } else if (status.status === 'Failed') {
            stopPolling();
            updateStatus('error', status.generation ?? 0);
            addLog(`Discovery failed: ${status.error ?? 'Unknown error'}`);
          } else {
            updateStatus('processing', status.generation ?? 0, status.best_score ?? 0);
          }
        } catch {
          stopPolling();
          updateStatus('error', 0);
          addLog('Lost connection while polling discovery status.');
        }
      }, POLL_INTERVAL_MS);

      return taskId;
    },
    [navigate, reset, setTaskId, stopPolling, updateStatus, addLog]
  );

  return { startDiscovery, stopPolling };
}
