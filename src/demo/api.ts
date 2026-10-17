import type { LayoutConfig } from '../adaptive';
import type { SessionRecord } from './sessionRecorder';

const API_URL = process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000';

export async function fetchLayout(): Promise<LayoutConfig> {
  const response = await fetch(`${API_URL}/api/layout`);
  if (!response.ok) {
    throw new Error(`Layout request failed: ${response.status}`);
  }
  return response.json();
}

export async function fetchPersonalizedLayout(
  preference: string,
): Promise<LayoutConfig> {
  const response = await fetch(`${API_URL}/api/layout/personalize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ preference }),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? `Request failed: ${response.status}`);
  }
  return response.json();
}

/**
 * Syncs a session record. Resolves on success or a permanent rejection (4xx);
 * rejects on network or server errors so the recorder retries later.
 */
export async function putSession(record: SessionRecord): Promise<void> {
  const { id, ...body } = record;
  const response = await fetch(`${API_URL}/api/sessions/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (response.status >= 500) throw new Error(`Session sync failed: ${response.status}`);
  if (!response.ok) console.warn(`Session ${id} rejected (${response.status})`);
}
