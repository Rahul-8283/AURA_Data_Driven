import { useCallback, useEffect, useRef, useState } from 'react';
import axios from 'axios';
import api from '../lib/api';
import { pollUntilDone } from '../lib/pollIngestionTask';
import type {
  IngestionSource,
  IngestionStatusResponse,
  IngestionSyncResponse,
  KnowledgeStatsResponse,
} from '../types/ingestion';

function requestErrorMessage(err: unknown): string {
  if (axios.isAxiosError(err)) {
    if (err.response?.status === 401 || err.response?.status === 403) return 'Please sign in again to sync literature.';
    const detail = (err.response?.data as { detail?: unknown } | undefined)?.detail;
    if (typeof detail === 'string') return detail;
    if (err.response?.status === 422) return 'The server rejected that topic. Use 2 to 200 characters.';
  }
  return 'Failed to trigger literature sync.';
}

const fetchStatus = (taskId: string) => (signal: AbortSignal) =>
  api.get<IngestionStatusResponse>(`/api/v1/ingestion/status/${taskId}`, { signal }).then((res) => res.data);

export function useIngestionSync() {
  const [stats, setStats] = useState<KnowledgeStatsResponse | null>(null);
  const [loadingStats, setLoadingStats] = useState(true);
  const [statsUnavailable, setStatsUnavailable] = useState(false);

  const [isSyncing, setIsSyncing] = useState(false);
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null);
  const [taskStatus, setTaskStatus] = useState<IngestionStatusResponse | null>(null);
  const [extractionStatus, setExtractionStatus] = useState<IngestionStatusResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState('');
  const controllerRef = useRef<AbortController | null>(null);

  const loadStats = useCallback(async () => {
    try {
      const { data } = await api.get<KnowledgeStatsResponse>('/api/v1/ingestion/stats');
      setStats(data);
      setStatsUnavailable(false);
    } catch {
      setStatsUnavailable(true);
    } finally {
      setLoadingStats(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    api.get<KnowledgeStatsResponse>('/api/v1/ingestion/stats')
      .then(({ data }) => {
        if (!active) return;
        setStats(data);
        setStatsUnavailable(false);
      })
      .catch(() => {
        if (active) setStatsUnavailable(true);
      })
      .finally(() => {
        if (active) setLoadingStats(false);
      });
    return () => { active = false; };
  }, []);

  useEffect(() => () => controllerRef.current?.abort(), []);

  const refreshStats = useCallback(() => {
    setLoadingStats(true);
    void loadStats();
  }, [loadStats]);

  const startSync = useCallback(async (query: string, sources: IngestionSource[]) => {
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;

    setIsSyncing(true);
    setErrorMsg('');
    setTaskStatus(null);
    setExtractionStatus(null);

    try {
      const { data } = await api.post<IngestionSyncResponse>('/api/v1/ingestion/sync', {
        query,
        sources,
        max_results: 10,
      });
      setActiveTaskId(data.task_id);
      setTaskStatus({ status: 'In Progress', stage: 'fetching', message: 'Initiated background literature harvester...' });

      const harvest = await pollUntilDone(fetchStatus(data.task_id), setTaskStatus, controller.signal);
      if (!harvest || controller.signal.aborted) return;
      setTaskStatus(harvest);
      setIsSyncing(false);
      void loadStats();

      if (harvest.status === 'Complete' && harvest.extraction_task_id) {
        const extraction = await pollUntilDone(fetchStatus(harvest.extraction_task_id), setExtractionStatus, controller.signal);
        if (extraction && !controller.signal.aborted) {
          setExtractionStatus(extraction);
          void loadStats();
        }
      }
    } catch (err) {
      if (!controller.signal.aborted) {
        setErrorMsg(requestErrorMessage(err));
        setIsSyncing(false);
      }
    }
  }, [loadStats]);

  return {
    stats, loadingStats, statsUnavailable, refreshStats,
    isSyncing, activeTaskId, taskStatus, extractionStatus, errorMsg, startSync,
  };
}
