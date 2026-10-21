import assert from 'node:assert/strict';
import { test } from 'node:test';
import { pollUntilDone } from '../src/lib/pollIngestionTask.ts';
import type { IngestionStatusResponse } from '../src/types/ingestion.ts';

const FAST = { intervalMs: 5, maxWaitMs: 2000 };
const running = (message = 'working'): IngestionStatusResponse => ({ status: 'In Progress', message });
const done: IngestionStatusResponse = { status: 'Complete', message: 'finished' };

// Hands out the given outcomes in order; an Error is thrown, anything else is returned.
function scripted(outcomes: Array<IngestionStatusResponse | Error>) {
  const calls = { count: 0 };
  const fetchStatus = async () => {
    const next = outcomes[Math.min(calls.count++, outcomes.length - 1)];
    if (next instanceof Error) throw next;
    return next;
  };
  return { fetchStatus, calls };
}

test('reports every interim status and returns the final one', async () => {
  const { fetchStatus } = scripted([running('a'), running('b'), done]);
  const seen: string[] = [];

  const result = await pollUntilDone(fetchStatus, (s) => seen.push(s.status), new AbortController().signal, FAST);

  assert.deepEqual(result, done);
  assert.deepEqual(seen, ['In Progress', 'In Progress', 'Complete']);
});

test('a Failed task is returned as-is so its error can be shown', async () => {
  const failure: IngestionStatusResponse = { status: 'Failed', error: 'All literature sources failed' };

  const result = await pollUntilDone(scripted([running(), failure]).fetchStatus, () => {}, new AbortController().signal, FAST);

  assert.deepEqual(result, failure);
});

test('gives up with a Failed status after repeated request errors instead of spinning forever', async () => {
  const { fetchStatus, calls } = scripted([new Error('offline')]);

  const result = await pollUntilDone(fetchStatus, () => {}, new AbortController().signal, FAST);

  assert.equal(result?.status, 'Failed');
  assert.match(result?.error ?? '', /Lost connection/);
  assert.equal(calls.count, 3);
});

test('an isolated error does not count against later polls', async () => {
  const { fetchStatus } = scripted([new Error('blip'), running(), new Error('blip'), new Error('blip'), running(), done]);

  const result = await pollUntilDone(fetchStatus, () => {}, new AbortController().signal, FAST);

  assert.deepEqual(result, done);
});

test('a worker that never finishes ends in a timeout failure', async () => {
  const result = await pollUntilDone(scripted([running()]).fetchStatus, () => {}, new AbortController().signal, { intervalMs: 5, maxWaitMs: 40 });

  assert.equal(result?.status, 'Failed');
  assert.match(result?.error ?? '', /Timed out/);
});

test('aborting stops polling immediately and returns null', async () => {
  const controller = new AbortController();
  const { fetchStatus, calls } = scripted([running()]);
  const pending = pollUntilDone(fetchStatus, () => {}, controller.signal, { intervalMs: 1000, maxWaitMs: 60_000 });

  await new Promise((resolve) => setTimeout(resolve, 20));
  controller.abort();
  const result = await pending;
  const callsAtAbort = calls.count;
  await new Promise((resolve) => setTimeout(resolve, 30));

  assert.equal(result, null);
  assert.equal(calls.count, callsAtAbort);
});

test('an aborted signal never issues a request', async () => {
  const controller = new AbortController();
  controller.abort();
  const { fetchStatus, calls } = scripted([done]);

  assert.equal(await pollUntilDone(fetchStatus, () => {}, controller.signal, FAST), null);
  assert.equal(calls.count, 0);
});

test('requests never overlap, even when the server is slower than the poll interval', async () => {
  let inFlight = 0;
  let maxInFlight = 0;
  let calls = 0;
  const fetchStatus = async () => {
    inFlight += 1;
    maxInFlight = Math.max(maxInFlight, inFlight);
    await new Promise((resolve) => setTimeout(resolve, 25));
    inFlight -= 1;
    return ++calls >= 4 ? done : running();
  };

  await pollUntilDone(fetchStatus, () => {}, new AbortController().signal, { intervalMs: 5, maxWaitMs: 5000 });

  assert.equal(maxInFlight, 1);
});
