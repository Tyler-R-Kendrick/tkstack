type Waiting = { resolve: () => void; reject: (error: unknown) => void; signal: AbortSignal; abort: () => void };

/** One shared capacity budget per runtime, including harness turns. */
export function createLimiter(capacity: number, maxPending: number) {
  let active = 0;
  const waiting: Waiting[] = [];
  async function acquire(signal: AbortSignal) {
    signal.throwIfAborted();
    if (active < capacity) { active++; return; }
    if (waiting.length >= maxPending) throw new Error('Runtime capacity exceeded');
    await new Promise<void>((resolve, reject) => {
      const entry: Waiting = { resolve, reject, signal, abort: () => {
        const index = waiting.indexOf(entry);
        if (index >= 0) { waiting.splice(index, 1); reject(signal.reason); }
      } };
      waiting.push(entry);
      signal.addEventListener('abort', entry.abort, { once: true });
    });
  }
  function release() {
    const next = waiting.shift();
    if (!next) { active--; return; }
    next.signal.removeEventListener('abort', next.abort);
    // Transfer the reserved permit before waking its new owner.
    next.resolve();
  }
  return async <T>(operation: () => Promise<T>, signal: AbortSignal): Promise<T> => {
    await acquire(signal);
    try { signal.throwIfAborted(); return await operation(); }
    finally { release(); }
  };
}
