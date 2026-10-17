import type { LayoutConfig } from '../adaptive';

export type LayoutSource = 'static' | 'ai' | 'fallback';

export type SessionRecord = {
  id: string;
  layoutSource: LayoutSource;
  preference: string | null;
  layout: LayoutConfig;
  startedAt: string;
  interactionCount: number;
  completedAt: string | null;
};

/** Resolves when the server has the record; rejects if it should be retried later. */
type Send = (record: SessionRecord) => Promise<void>;

function newId(): string {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = Math.floor(Math.random() * 16);
    return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16);
  });
}

/**
 * Keeps session records in memory and syncs each one, whole, to the server.
 * Writes are cumulative and idempotent, so a failed write is simply retried
 * (on the next interaction, completion or new session) without double counting.
 */
export function createSessionRecorder(send: Send) {
  const sessions = new Map<string, { record: SessionRecord; version: number; syncedVersion: number }>();
  let flushing = false;
  let flushAgain = false;

  async function flush() {
    if (flushing) {
      flushAgain = true;
      return;
    }
    flushing = true;
    try {
      do {
        flushAgain = false;
        for (const entry of [...sessions.values()]) {
          if (entry.syncedVersion === entry.version) continue;
          const { record, version } = entry;
          try {
            await send(record);
            entry.syncedVersion = Math.max(entry.syncedVersion, version);
          } catch {
            // Stays dirty; retried on the next trigger.
          }
        }
      } while (flushAgain);
    } finally {
      flushing = false;
    }
  }

  function update(id: string, change: (record: SessionRecord) => SessionRecord | null) {
    const entry = sessions.get(id);
    if (!entry) return;
    const next = change(entry.record);
    if (!next) return;
    entry.record = next;
    entry.version += 1;
    void flush();
  }

  return {
    /** Starts a new measured experience; also retries any unsent records. */
    startSession(init: { layoutSource: LayoutSource; preference: string | null; layout: LayoutConfig }): string {
      const id = newId();
      const record: SessionRecord = {
        id,
        ...init,
        startedAt: new Date().toISOString(),
        interactionCount: 0,
        completedAt: null,
      };
      sessions.set(id, { record, version: 1, syncedVersion: 0 });
      void flush();
      return id;
    },
    /** Counts one interaction for exactly this session; ignored once it is completed. */
    recordInteraction(id: string) {
      update(id, (r) => (r.completedAt ? null : { ...r, interactionCount: r.interactionCount + 1 }));
    },
    /** Completes this session once; later calls keep the first completion time. */
    complete(id: string) {
      update(id, (r) => (r.completedAt ? null : { ...r, completedAt: new Date().toISOString() }));
    },
    /** Resolves when the current flush has finished (used by tests). */
    idle: async () => {
      while (flushing) await new Promise((resolve) => setTimeout(resolve, 0));
    },
    get: (id: string) => sessions.get(id)?.record,
    isSynced: (id: string) => {
      const entry = sessions.get(id);
      return !!entry && entry.syncedVersion === entry.version;
    },
  };
}
