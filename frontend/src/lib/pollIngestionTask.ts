import type { IngestionStatusResponse } from '../types/ingestion';

export interface PollOptions {
  intervalMs?: number;
  maxConsecutiveErrors?: number;
  maxWaitMs?: number;
}

const DEFAULTS = {
  intervalMs: 2500,
  maxConsecutiveErrors: 3,
  maxWaitMs: 10 * 60 * 1000,
};

const failed = (error: string): IngestionStatusResponse => ({ status: 'Failed', stage: 'failed', error });

function sleep(ms: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolve) => {
    const timer = setTimeout(resolve, ms);
    signal.addEventListener('abort', () => { clearTimeout(timer); resolve(); }, { once: true });
  });
}

/**
 * Polls one ingestion task until it finishes. Requests never overlap (each waits for the previous),
 * a run of failed polls or a stalled worker ends in a Failed status instead of an endless spinner,
 * and aborting the signal stops it and returns null.
 */
export async function pollUntilDone(
  fetchStatus: (signal: AbortSignal) => Promise<IngestionStatusResponse>,
  onStatus: (status: IngestionStatusResponse) => void,
  signal: AbortSignal,
  options: PollOptions = {},
): Promise<IngestionStatusResponse | null> {
  const { intervalMs, maxConsecutiveErrors, maxWaitMs } = { ...DEFAULTS, ...options };
  const startedAt = Date.now();
  let consecutiveErrors = 0;

  while (!signal.aborted) {
    try {
      const status = await fetchStatus(signal);
      consecutiveErrors = 0;
      onStatus(status);
      if (status.status === 'Complete' || status.status === 'Failed') return status;
    } catch {
      if (signal.aborted) return null;
      consecutiveErrors += 1;
      if (consecutiveErrors >= maxConsecutiveErrors) {
        return failed('Lost connection to the server while checking progress.');
      }
    }
    if (Date.now() - startedAt > maxWaitMs) {
      return failed('Timed out waiting for the worker. Check that the Celery worker is running.');
    }
    await sleep(intervalMs, signal);
  }
  return null;
}
